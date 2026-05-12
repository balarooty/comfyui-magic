# Memory Optimization Patterns

## When to Use

Use these patterns when your node processes **large tensors, models, or batches** that may exceed available VRAM or RAM. Common cases:

- Loading large models (SDXL, video models, 3D models)
- Processing high-resolution images (4K+)
- Batch processing many images
- Video frame processing
- 3D data (point clouds, meshes, volumetric)

Key techniques: **device management**, **model offloading**, **quantization**, **tiled processing**, **gradient checkpointing**, and **memory cleanup**.

---

## Complete Working Example: Memory-Optimized Processing Node

```python
# nodes_memory_opt.py

import gc
import logging
import torch
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device Management Utilities
# ---------------------------------------------------------------------------

def get_device_info():
    """Return available devices and their memory status."""
    info = {
        "cpu": True,
        "cuda": torch.cuda.is_available(),
        "mps": hasattr(torch.backends, "mps") and torch.backends.mps.is_available(),
    }

    if info["cuda"]:
        info["cuda_total"] = torch.cuda.get_device_properties(0).total_mem
        info["cuda_free"] = torch.cuda.mem_get_info(0)[0]
        info["cuda_used"] = info["cuda_total"] - info["cuda_free"]

    return info


def get_best_device(preference="auto"):
    """Select the best available device."""
    if preference == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")
    return torch.device(preference)


def free_memory(device=None):
    """Aggressively free unused memory."""
    gc.collect()
    if device is None or device.type == "cuda":
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    if device is None or device.type == "mps":
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            if hasattr(torch.mps, "empty_cache"):
                torch.mps.empty_cache()


def get_tensor_memory_mb(tensor):
    """Calculate memory usage of a tensor in MB."""
    return tensor.element_size() * tensor.nelement() / (1024 * 1024)


# ---------------------------------------------------------------------------
# Model Offloading
# ---------------------------------------------------------------------------

class ModelOffloader:
    """
    Context manager that moves a model between CPU and GPU on demand.

    Usage:
        offloader = ModelOffloader(model, device="cuda")
        with offloader:
            output = model(input)  # model is on GPU here
        # model is back on CPU, GPU memory freed
    """

    def __init__(self, model, device="cuda", free_after=True):
        self.model = model
        self.device = torch.device(device)
        self.cpu = torch.device("cpu")
        self.free_after = free_after
        self.original_device = None

    def __enter__(self):
        # Move model to target device
        self.model.to(self.device)
        return self.model

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Move model back to CPU and free GPU memory
        if self.free_after:
            self.model.to(self.cpu)
            free_memory(self.device)
        return False


class ModelOffloadNode:
    """Load a model with automatic CPU offloading to save VRAM."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "offload_device": (["cpu", "cuda", "mps", "auto"],),
                "free_after_use": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "setup_offload"
    CATEGORY = "model"

    def setup_offload(self, model, offload_device, free_after_use):
        device = get_best_device(offload_device) if offload_device == "auto" else torch.device(offload_device)

        # Store offloader reference on the model
        model._offloader = ModelOffloader(model.model, device=device, free_after=free_after_use)
        return (model,)


# ---------------------------------------------------------------------------
# Quantization Support
# ---------------------------------------------------------------------------

def quantize_model_int8(model):
    """Apply INT8 dynamic quantization to a model."""
    try:
        quantized = torch.quantization.quantize_dynamic(
            model,
            {torch.nn.Linear, torch.nn.Conv2d},
            dtype=torch.qint8,
        )
        return quantized
    except Exception as e:
        logger.warning(f"INT8 quantization failed: {e}. Returning original model.")
        return model


def quantize_model_int4_weights_only(weight_tensor):
    """Simulate INT4 weight quantization (approximate)."""
    # Symmetric quantization to 4-bit range
    abs_max = weight_tensor.abs().max()
    scale = abs_max / 7.0  # 4-bit signed range: -8 to 7
    quantized = torch.clamp(torch.round(weight_tensor / scale), -8, 7).to(torch.int8)
    return quantized, scale


class QuantizeModelNode:
    """Apply quantization to a model to reduce memory usage."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "precision": (["fp32", "fp16", "bf16", "int8"],),
                "device": (["auto", "cpu", "cuda", "mps"],),
            },
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "quantize"
    CATEGORY = "model"

    def quantize(self, model, precision, device):
        target_device = get_best_device(device) if device == "auto" else torch.device(device)

        if precision == "fp32":
            model.model = model.model.float().to(target_device)
        elif precision == "fp16":
            model.model = model.model.half().to(target_device)
        elif precision == "bf16":
            model.model = model.model.to(torch.bfloat16).to(target_device)
        elif precision == "int8":
            model.model = quantize_model_int8(model.model)

        mem_mb = sum(
            p.element_size() * p.nelement()
            for p in model.model.parameters()
        ) / (1024 * 1024)
        logger.info(f"Model after {precision} quantization: {mem_mb:.1f} MB on {target_device}")

        return (model,)


# ---------------------------------------------------------------------------
# Tiled Processing
# ---------------------------------------------------------------------------

def tiled_process_2d(
    tensor,
    process_fn,
    tile_size=512,
    tile_overlap=64,
    channel_last=True,
):
    """
    Process a large 2D tensor in overlapping tiles to avoid OOM.

    Args:
        tensor: (B, H, W, C) if channel_last, else (B, C, H, W)
        process_fn: function that takes a tile tensor and returns processed tile
        tile_size: size of each tile
        tile_overlap: overlap between adjacent tiles
        channel_last: tensor layout

    Returns:
        Processed tensor of same shape
    """
    if channel_last:
        b, h, w, c = tensor.shape
    else:
        b, c, h, w = tensor.shape

    # If tensor fits in memory, process directly
    if h <= tile_size and w <= tile_size:
        return process_fn(tensor)

    result = torch.zeros_like(tensor)
    weight = torch.zeros(b, h, w, 1 if channel_last else 1, device=tensor.device, dtype=tensor.dtype)

    step = tile_size - tile_overlap

    for y in range(0, h, step):
        for x in range(0, w, step):
            # Calculate tile boundaries
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            y_start = max(0, y_end - tile_size)
            x_start = max(0, x_end - tile_size)

            # Extract tile
            if channel_last:
                tile = tensor[:, y_start:y_end, x_start:x_end, :].clone()
            else:
                tile = tensor[:, :, y_start:y_end, x_start:x_end].clone()

            # Process tile
            processed = process_fn(tile)

            # Create blending weight (ramp at edges)
            tile_h = y_end - y_start
            tile_w = x_end - x_start
            wy = torch.ones(tile_h, device=tensor.device, dtype=tensor.dtype)
            wx = torch.ones(tile_w, device=tensor.device, dtype=tensor.dtype)

            # Ramp at edges for smooth blending
            ramp_size = min(tile_overlap // 2, tile_h // 4, tile_w // 4)
            if ramp_size > 0:
                ramp = torch.linspace(0, 1, ramp_size, device=tensor.device, dtype=tensor.dtype)
                wy[:ramp_size] = torch.min(wy[:ramp_size], ramp)
                wy[-ramp_size:] = torch.min(wy[-ramp_size:], ramp.flip(0))
                wx[:ramp_size] = torch.min(wx[:ramp_size], ramp)
                wx[-ramp_size:] = torch.min(wx[-ramp_size:], ramp.flip(0))

            blend = wy.unsqueeze(1) * wx.unsqueeze(0)
            blend = blend.unsqueeze(0).unsqueeze(-1 if channel_last else 1)

            # Accumulate
            if channel_last:
                result[:, y_start:y_end, x_start:x_end, :] += processed * blend
                weight[:, y_start:y_end, x_start:x_end, :] += blend
            else:
                result[:, :, y_start:y_end, x_start:x_end] += processed * blend
                weight[:, :, y_start:y_end, x_start:x_end] += blend

            # Free tile memory
            del tile, processed
            free_memory(tensor.device)

    # Normalize by blending weights
    weight = weight.clamp(min=1e-8)
    if channel_last:
        result = result / weight
    else:
        result = result / weight

    return result


class TiledImageProcessNode:
    """Process large images in tiles to avoid out-of-memory errors."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "tile_size": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}),
                "tile_overlap": ("INT", {"default": 64, "min": 0, "max": 512, "step": 16}),
                "operation": (["blur", "sharpen", "edge_detect"],),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "image"

    def process(self, image, tile_size, tile_overlap, operation, strength):
        from PIL import Image as PILImage, ImageFilter, ImageEnhance

        def process_tile(tile_tensor):
            # Convert to PIL
            arr = tile_tensor[0].cpu().numpy()
            arr = (arr * 255).clip(0, 255).astype(np.uint8)
            pil_img = PILImage.fromarray(arr)

            if operation == "blur":
                pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=strength * 5))
            elif operation == "sharpen":
                enhancer = ImageEnhance.Sharpness(pil_img)
                pil_img = enhancer.enhance(1.0 + strength)
            elif operation == "edge_detect":
                pil_img = pil_img.filter(ImageFilter.FIND_EDGES)

            # Convert back to tensor
            arr = np.array(pil_img).astype(np.float32) / 255.0
            return torch.from_numpy(arr).unsqueeze(0).to(tile_tensor.device)

        result = tiled_process_2d(
            image,
            process_fn=process_tile,
            tile_size=tile_size,
            tile_overlap=tile_overlap,
            channel_last=True,
        )

        return (result,)


# ---------------------------------------------------------------------------
# Gradient Checkpointing (for training/fine-tuning nodes)
# ---------------------------------------------------------------------------

def enable_gradient_checkpointing(model):
    """Enable gradient checkpointing on supported model types."""
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        logger.info("Gradient checkpointing enabled via model method")
        return True

    # Manual approach: wrap specific submodules
    for name, module in model.named_modules():
        if hasattr(module, "gradient_checkpointing"):
            module.gradient_checkpointing = True
            logger.info(f"Gradient checkpointing enabled on {name}")

    return False


# ---------------------------------------------------------------------------
# VRAM Monitor Node
# ---------------------------------------------------------------------------

class VRAMMonitorNode:
    """Displays current VRAM usage and provides optimization recommendations."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trigger": ("IMAGE",),  # Any input to trigger execution
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT", "FLOAT",)
    RETURN_NAMES = ("report", "used_gb", "free_gb",)
    FUNCTION = "monitor"
    CATEGORY = "debug"

    def monitor(self, trigger):
        info = get_device_info()

        lines = ["=== VRAM Status ==="]

        if info["cuda"]:
            total_gb = info["cuda_total"] / (1024 ** 3)
            free_gb = info["cuda_free"] / (1024 ** 3)
            used_gb = info["cuda_used"] / (1024 ** 3)
            pct = (used_gb / total_gb) * 100

            lines.append(f"Device: {torch.cuda.get_device_name(0)}")
            lines.append(f"Total: {total_gb:.2f} GB")
            lines.append(f"Used:  {used_gb:.2f} GB ({pct:.1f}%)")
            lines.append(f"Free:  {free_gb:.2f} GB")
            lines.append("")

            if pct > 90:
                lines.append("WARNING: VRAM usage >90%")
                lines.append("Recommendations:")
                lines.append("  - Use tiled processing for large images")
                lines.append("  - Enable model offloading")
                lines.append("  - Use fp16/bf16 precision")
                lines.append("  - Reduce batch size")
            elif pct > 70:
                lines.append("NOTE: VRAM usage >70%, consider optimization")
            else:
                lines.append("VRAM usage is healthy")

            return ("\n".join(lines), used_gb, free_gb)
        else:
            lines.append("No CUDA device available")
            return ("\n".join(lines), 0.0, 0.0)


# ---------------------------------------------------------------------------
# Batch Processing with Memory Limit
# ---------------------------------------------------------------------------

class BatchProcessNode:
    """Process images in memory-limited batches."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "max_vram_gb": ("FLOAT", {"default": 4.0, "min": 0.5, "max": 24.0, "step": 0.5}),
                "operation": (["normalize", "clamp", "invert"],),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process_batch"
    CATEGORY = "image"

    def process_batch(self, images, max_vram_gb, operation):
        batch_size = images.shape[0]
        max_bytes = max_vram_gb * (1024 ** 3)

        # Estimate per-image memory
        per_image_bytes = images[0].element_size() * images[0].nelement()
        safe_batch = max(1, int(max_bytes * 0.7 / per_image_bytes))  # 70% safety margin

        logger.info(f"Processing {batch_size} images in batches of {safe_batch}")

        results = []
        for i in range(0, batch_size, safe_batch):
            chunk = images[i:i + safe_batch]

            if operation == "normalize":
                chunk = chunk / chunk.max().clamp(min=1e-8)
            elif operation == "clamp":
                chunk = chunk.clamp(0, 1)
            elif operation == "invert":
                chunk = 1.0 - chunk

            results.append(chunk.detach())

            if i + safe_batch < batch_size:
                free_memory(images.device)

        return (torch.cat(results, dim=0),)


# ---------------------------------------------------------------------------
# Weight Caching
# ---------------------------------------------------------------------------

class WeightCache:
    """
    LRU cache for model weights on GPU.
    Keeps most-recently-used weights on GPU, evicts oldest to CPU.
    """

    def __init__(self, max_items=3):
        self.max_items = max_items
        self.cache = {}  # key -> (tensor_on_gpu, tensor_on_cpu)
        self.access_order = []

    def get(self, key, cpu_tensor, device="cuda"):
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key][0]

        # Evict if needed
        while len(self.cache) >= self.max_items:
            evict_key = self.access_order.pop(0)
            gpu_tensor, cpu_tensor_cached = self.cache.pop(evict_key)
            del gpu_tensor
            free_memory(torch.device(device))

        # Load to GPU
        gpu_tensor = cpu_tensor.to(device)
        self.cache[key] = (gpu_tensor, cpu_tensor)
        self.access_order.append(key)
        return gpu_tensor

    def clear(self):
        for gpu_tensor, _ in self.cache.values():
            del gpu_tensor
        self.cache.clear()
        self.access_order.clear()
        free_memory()


# Global cache instance
_global_weight_cache = WeightCache(max_items=3)


class CachedModelLoadNode:
    """Load model weights with LRU GPU caching."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "cache_key": ("STRING", {"default": "model_0"}),
                "device": (["cuda", "mps", "cpu"],),
            },
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "load_cached"
    CATEGORY = "model"

    def load_cached(self, model, cache_key, device):
        target = torch.device(device)

        # Cache individual parameter tensors
        for name, param in model.model.named_parameters():
            cache_key_param = f"{cache_key}.{name}"
            if param.device != target:
                cached = _global_weight_cache.get(cache_key_param, param.data, device=target)
                param.data = cached

        return (model,)


# ---------------------------------------------------------------------------
# Node Registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "ModelOffloadNode": ModelOffloadNode,
    "QuantizeModelNode": QuantizeModelNode,
    "TiledImageProcessNode": TiledImageProcessNode,
    "VRAMMonitorNode": VRAMMonitorNode,
    "BatchProcessNode": BatchProcessNode,
    "CachedModelLoadNode": CachedModelLoadNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ModelOffloadNode": "Model Offload",
    "QuantizeModelNode": "Quantize Model",
    "TiledImageProcessNode": "Tiled Image Process",
    "VRAMMonitorNode": "VRAM Monitor",
    "BatchProcessNode": "Batch Process (Memory-Limited)",
    "CachedModelLoadNode": "Cached Model Load",
}
```

---

## Key Patterns Summary

### 1. Device Management

```python
# Always check device availability
if torch.cuda.is_available():
    device = torch.device("cuda")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

# Move tensors explicitly
tensor = tensor.to(device)

# Free memory when done
del tensor
torch.cuda.empty_cache()
```

### 2. Model Offloading (CPU ↔ GPU)

```python
# Move to GPU for computation
model.to("cuda")
output = model(input)

# Move back to CPU to free VRAM
model.to("cpu")
torch.cuda.empty_cache()
```

### 3. Tiled Processing

```python
# Split large image into overlapping tiles
# Process each tile independently
# Blend tiles back together with smooth weights
result = tiled_process_2d(image, process_fn, tile_size=512, tile_overlap=64)
```

### 4. Quantization

```python
# FP16: halves memory, minimal quality loss
model.half()

# BF16: better numerical stability than FP16
model.to(torch.bfloat16)

# INT8: quarter memory, some quality loss
quantized = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
```

---

## Key Considerations

| Concern | Guidance |
|---|---|
| **`torch.cuda.empty_cache()`** | Call after `del`-ing large tensors. Does not free memory held by tensors still in scope. |
| **`.to()` vs `.cuda()`** | Use `.to(device)` for portability. `.cuda()` hardcodes CUDA. |
| **In-place ops** | Prefer `tensor.mul_(2)` over `tensor = tensor * 2` to avoid allocating a new tensor. |
| **`torch.no_grad()`** | Always wrap inference in `with torch.no_grad():` to avoid storing computation graphs. |
| **`del` + `gc.collect()`** | Python's GC may not immediately free tensors. Explicit `del` + `gc.collect()` helps. |
| **MPS limitations** | Apple MPS backend has gaps. Some ops fall back to CPU silently, which can cause slowdowns and memory spikes. |
| **FP16 on CPU** | CPU does not natively accelerate FP16. Use FP32 on CPU, FP16 on GPU. |
| **Tile overlap** | Too little overlap causes visible seams. Too much wastes computation. 32–128px is typical. |
| **Batch size estimation** | Calculate per-sample memory and divide available VRAM by it. Use 70–80% of free VRAM as a safety margin. |

---

## Variations

### 1. Automatic Mixed Precision (AMP)

```python
def process_with_amp(model, input_tensor, device):
    with torch.no_grad():
        with torch.autocast(device_type=device.type, dtype=torch.float16):
            output = model(input_tensor)
    return output.float()  # Convert back to FP32
```

### 2. Sliding Window for Large Latents

```python
def process_large_latent(latent, model, window_size=64):
    """Process a large latent tensor with a sliding window."""
    b, c, h, w = latent.shape
    result = torch.zeros_like(latent)
    count = torch.zeros_like(latent)

    for y in range(0, h, window_size // 2):
        for x in range(0, w, window_size // 2):
            y_end = min(y + window_size, h)
            x_end = min(x + window_size, w)
            tile = latent[:, :, y:y_end, x:x_end]

            with torch.no_grad():
                processed = model(tile)

            result[:, :, y:y_end, x:x_end] += processed
            count[:, :, y:y_end, x:x_end] += 1

    return result / count.clamp(min=1)
```

### 3. Sequential Offloading for Multi-Stage Pipelines

```python
def sequential_offload_pipeline(stages, input_data, device="cuda"):
    """Run multiple model stages, offloading each after use."""
    current = input_data

    for i, (model, process_fn) in enumerate(stages):
        logger.info(f"Stage {i}: loading model to {device}")
        model.to(device)

        with torch.no_grad():
            current = process_fn(model, current)

        model.to("cpu")
        free_memory(torch.device(device))
        logger.info(f"Stage {i}: offloaded model, freed memory")

    return current
```

### 4. Memory-Mapped Large Files

```python
import numpy as np

def load_large_image_mmap(path):
    """Load a very large image using memory mapping."""
    # Memory-map the file instead of loading it entirely into RAM
    mmap_arr = np.memmap(path, dtype=np.float32, mode="r", shape=(1, 4096, 4096, 3))

    # Process in chunks
    chunk_size = 512
    results = []
    for i in range(0, mmap_arr.shape[1], chunk_size):
        chunk = torch.from_numpy(mmap_arr[0, i:i+chunk_size].copy())
        # process chunk...
        results.append(chunk)

    return torch.cat(results, dim=0)
```

### 5. VRAM-Aware Auto-Batching

```python
def auto_batch_process(images, process_fn, device="cuda", safety_frac=0.75):
    """Automatically determine batch size based on available VRAM."""
    if device == "cuda":
        free_mem = torch.cuda.mem_get_info(0)[0]
    else:
        free_mem = 8 * (1024 ** 3)  # Assume 8GB for non-CUDA

    per_image = images[0].element_size() * images[0].nelement()
    batch_size = max(1, int(free_mem * safety_frac / per_image))

    results = []
    for i in range(0, len(images), batch_size):
        batch = images[i:i+batch_size].to(device)
        with torch.no_grad():
            results.append(process_fn(batch).cpu())
        del batch
        free_memory(torch.device(device))

    return torch.cat(results, dim=0)
```
