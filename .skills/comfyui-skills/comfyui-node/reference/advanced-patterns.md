# Advanced Patterns Reference

Expert-level patterns for ComfyUI custom node development.

## Dynamic Outputs

Nodes that produce a variable number of outputs based on input parameters.

```python
class DynamicSplitter:
    RETURN_TYPES = tuple(["IMAGE"] * 50)  # Maximum possible outputs

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "count": ("INT", {"default": 2, "min": 1, "max": 50}),
            }
        }

    FUNCTION = "split"
    CATEGORY = "image/batch"

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, count=1, **kwargs):
        return tuple(["IMAGE"] * int(count))

    @classmethod
    def get_output_names(cls, count=1, **kwargs):
        return tuple([f"image_{i+1}" for i in range(int(count))])

    def split(self, image, count):
        chunks = torch.chunk(image, int(count), dim=0)
        return tuple(chunks)
```

## Model Patching

Clone and modify model behavior without altering the original.

```python
class AttentionOverride:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 5.0}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch"
    CATEGORY = "model/patching"

    def patch(self, model, scale):
        model_clone = model.clone()

        # Store custom parameters in model_options
        model_clone.model_options["transformer_options"]["attention_scale"] = scale

        # Inject into the processing pipeline
        model_clone.set_model_attn1_patch(self.attention_patch)

        return (model_clone,)

    def attention_patch(self, q, k, v, extra_options):
        scale = extra_options["transformer_options"].get("attention_scale", 1.0)
        return q, k * scale, v
```

### model.clone()

Creates a shallow copy of the model. Changes to the clone don't affect the original.

```python
model_clone = model.clone()
```

### model_options and transformer_options

Store custom parameters that are accessible during inference.

```python
model_clone.model_options["my_custom_param"] = value
model_clone.model_options["transformer_options"]["my_param"] = value

# Access in patches via extra_options
def my_patch(self, *args, extra_options):
    value = extra_options["model_options"].get("my_custom_param")
    value = extra_options["transformer_options"].get("my_param")
```

### set_model_attn1_patch

Override self-attention computation.

```python
def my_attn1_patch(self, q, k, v, extra_options):
    # q, k, v: query, key, value tensors
    # Modify and return
    return q, k, v

model_clone.set_model_attn1_patch(my_attn1_patch)
```

### set_model_attn2_patch

Override cross-attention computation.

```python
def my_attn2_patch(self, q, k, v, extra_options):
    return q, k, v

model_clone.set_model_attn2_patch(my_attn2_patch)
```

### set_model_unet_function_wrapper

Override the entire UNet forward pass.

```python
def my_unet_wrapper(apply_model, args):
    # args contains: input, timestep, cond, uncond, etc.
    result = apply_model(args["input"], args["timestep"], **args["cond"])
    return result

model_clone.set_model_unet_function_wrapper(my_unet_wrapper)
```

## Monkey-Patching

Inject custom behavior into model forward methods.

```python
class CrossAttentionInjector:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "style_image": ("IMAGE",),
                "injection_strength": ("FLOAT", {"default": 1.0}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "inject"
    CATEGORY = "model/patching"

    def inject(self, model, style_image, injection_strength):
        model_clone = model.clone()

        # Store style features for injection
        style_features = self.extract_features(style_image)
        model_clone.model_options["transformer_options"]["style_features"] = style_features
        model_clone.model_options["transformer_options"]["injection_strength"] = injection_strength

        # Patch cross-attention
        model_clone.set_model_attn2_patch(self.style_injection)

        return (model_clone,)

    def style_injection(self, q, k, v, extra_options):
        strength = extra_options["transformer_options"].get("injection_strength", 1.0)
        style = extra_options["transformer_options"].get("style_features")

        if style is not None and strength > 0:
            # Blend style features into cross-attention
            k = k * (1 - strength) + style * strength

        return q, k, v

    def extract_features(self, image):
        # Extract features for style injection
        return image.mean(dim=1, keepdim=True)
```

## Custom Samplers

Implement custom noise, sampler, and guider interfaces.

### Custom Noise

```python
class PerlinNoise:
    """Generates Perlin noise instead of standard Gaussian noise."""

    def __init__(self, seed, scale=1.0):
        self.seed = seed
        self.scale = scale

    def generate_noise(self, latent):
        torch.manual_seed(self.seed)
        # Generate Perlin-like noise
        noise = torch.randn_like(latent)
        # Apply frequency scaling
        noise = noise * self.scale
        return noise

# Node to create custom noise
class PerlinNoiseNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
            }
        }

    RETURN_TYPES = ("NOISE",)
    FUNCTION = "create_noise"
    CATEGORY = "sampling/noise"

    def create_noise(self, seed, scale):
        return (PerlinNoise(seed, scale),)
```

### Custom Sampler

```python
class AdaptiveSampler:
    """Adjusts step size based on convergence."""

    def __init__(self, tolerance=0.01, max_steps=20):
        self.tolerance = tolerance
        self.max_steps = max_steps

    def sample(self, model, sigmas, latent, **kwargs):
        current = latent
        for i in range(len(sigmas) - 1):
            sigma = sigmas[i]
            sigma_next = sigmas[i + 1]

            # Standard Euler step
            denoised = model(current, sigma, **kwargs)
            d = (current - denoised) / sigma
            current = current + d * (sigma_next - sigma)

            # Check convergence
            if torch.abs(d).mean() < self.tolerance:
                break

        return current

# Node to create custom sampler
class AdaptiveSamplerNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "tolerance": ("FLOAT", {"default": 0.01, "min": 0.001, "max": 1.0}),
                "max_steps": ("INT", {"default": 20, "min": 1, "max": 100}),
            }
        }

    RETURN_TYPES = ("SAMPLER",)
    FUNCTION = "create_sampler"
    CATEGORY = "sampling/samplers"

    def create_sampler(self, tolerance, max_steps):
        return (AdaptiveSampler(tolerance, max_steps),)
```

## Memory Optimization

### Model Offloading

Move model components to CPU when not in use.

```python
class ModelOffload:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "offload_to": (["cpu", "disk"],),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "offload"
    CATEGORY = "model/optimization"

    def offload(self, model, offload_to):
        model_clone = model.clone()

        if offload_to == "cpu":
            model_clone.model_options["transformer_options"]["offload_device"] = "cpu"
        elif offload_to == "disk":
            model_clone.model_options["transformer_options"]["offload_device"] = "disk"

        return (model_clone,)
```

### Quantization

Apply quantization to reduce memory usage.

```python
class QuantizeModel:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "precision": (["fp16", "bf16", "int8"],),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "quantize"
    CATEGORY = "model/optimization"

    def quantize(self, model, precision):
        model_clone = model.clone()

        if precision == "fp16":
            model_clone.model_options["transformer_options"]["dtype"] = torch.float16
        elif precision == "bf16":
            model_clone.model_options["transformer_options"]["dtype"] = torch.bfloat16
        elif precision == "int8":
            model_clone.model_options["transformer_options"]["quantize"] = "int8"

        return (model_clone,)
```

### Tiled Processing

Process large images in tiles to reduce memory usage.

```python
class TiledProcessor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "tile_size": ("INT", {"default": 512, "min": 64, "max": 2048}),
                "overlap": ("INT", {"default": 64, "min": 0, "max": 256}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process_tiled"
    CATEGORY = "image/processing"

    def process_tiled(self, image, tile_size, overlap):
        b, h, w, c = image.shape
        result = torch.zeros_like(image)

        for y in range(0, h, tile_size - overlap):
            for x in range(0, w, tile_size - overlap):
                # Extract tile
                y_end = min(y + tile_size, h)
                x_end = min(x + tile_size, w)
                tile = image[:, y:y_end, x:x_end, :]

                # Process tile
                processed = self.process_tile(tile)

                # Blend with overlap
                result[:, y:y_end, x:x_end, :] = processed

        return (result,)

    def process_tile(self, tile):
        # Apply processing to individual tile
        return tile * 1.0  # Placeholder
```

## Custom Types

Define and use custom type strings for domain-specific data.

```python
# Define a custom type
RETURN_TYPES = ("STYLE_DATA",)
RETURN_NAMES = ("style",)

# Use the custom type in another node
("STYLE_DATA",)

# Custom types can be any uppercase string
RETURN_TYPES = ("EMBEDDING_VECTOR", "ATTENTION_MAP", "FEATURE_PYRAMID")
```

### Type Aliasing for Clarity

Use descriptive type names even if they're technically the same underlying type.

```python
# Instead of generic "IMAGE" for different purposes
RETURN_TYPES = ("SOURCE_IMAGE",)    # Original input
RETURN_TYPES = ("REFERENCE_IMAGE",) # Style reference
RETURN_TYPES = ("MASK_IMAGE",)      # Processing mask

# These are all IMAGE tensors but semantically different
```

## Lazy Evaluation

Defer expensive computations until the value is actually needed.

```python
class ExpensiveNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "enhance": ("BOOLEAN", {"default": True}),
                "enhanced_image": ("IMAGE", {"lazy": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "image/processing"

    def process(self, image, enhance, enhanced_image=None):
        if enhance:
            # enhanced_image is only evaluated when accessed
            return (enhanced_image,)
        return (image,)
```

## Raw Links

Access the raw link data instead of the resolved value.

```python
class RawLinkNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "data": ("STRING", {"rawLink": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "utility"

    def process(self, data):
        # data contains the raw link information
        # instead of the resolved value
        return (str(data),)
```

## INPUT_IS_LIST for Batch Processing

Receive all inputs as lists, even single connections.

```python
class BatchProcessor:
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "strengths": ("FLOAT",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process_batch"
    CATEGORY = "image/batch"

    def process_batch(self, images, strengths):
        results = []
        for img, strength in zip(images, strengths):
            results.append(img * strength)
        return (results,)
```

## OUTPUT_IS_LIST for Sequential Outputs

Produce outputs that are lists of items.

```python
class SequenceGenerator:
    RETURN_TYPES = ("IMAGE",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "generate"
    CATEGORY = "image/batch"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "count": ("INT", {"default": 4, "min": 1, "max": 100}),
            }
        }

    def generate(self, count):
        images = [torch.randn(1, 512, 512, 3) for _ in range(count)]
        return (images,)
```

## SEARCH_ALIASES for Discoverability

Extra keywords to help users find your node in search.

```python
class GaussianBlur:
    SEARCH_ALIASES = ["blur", "smooth", "gaussian", "filter", "soft", "defocus"]
    DESCRIPTION = "Applies Gaussian blur to an image"
```

## IS_CHANGED for Cache Control

Control when a node re-executes.

```python
class RandomNode:
    @classmethod
    def IS_CHANGED(cls, seed, **kwargs):
        # Re-execute when seed changes
        return seed

class TimeBasedNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always re-execute (use current time)
        import time
        return time.time()

class StaticNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Never re-execute (returns constant)
        return "static_value"
```

## VALIDATE_INPUTS for Input Validation

Validate inputs before execution.

```python
class ValidatedNode:
    @classmethod
    def VALIDATE_INPUTS(cls, image, strength, **kwargs):
        if not isinstance(image, torch.Tensor):
            return "image must be a tensor"
        if strength < 0 or strength > 1:
            return "strength must be between 0 and 1"
        return True

    # Accept all inputs
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True
```

## Conditional Node Availability

Use try/except to gracefully handle missing dependencies.

```python
NODE_CLASS_MAPPINGS = {}

# Always available
from .core_nodes import MathNode
NODE_CLASS_MAPPINGS["MathNode"] = MathNode

# Requires optional dependency
try:
    import cv2
    from .cv_nodes import EdgeDetectNode
    NODE_CLASS_MAPPINGS["EdgeDetectNode"] = EdgeDetectNode
except ImportError:
    pass

# Requires GPU
try:
    import torch
    if torch.cuda.is_available():
        from .gpu_nodes import GPUNode
        NODE_CLASS_MAPPINGS["GPUNode"] = GPUNode
except (ImportError, RuntimeError):
    pass
```

## Composite Pattern

Build complex nodes by combining simpler operations.

```python
class ImagePipeline:
    """Applies a configurable pipeline of image operations."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "blur_radius": ("INT", {"default": 0, "min": 0, "max": 20}),
                "brightness": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0}),
                "contrast": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0}),
                "sharpen": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "pipeline"
    CATEGORY = "image/processing"

    def pipeline(self, image, blur_radius, brightness, contrast, sharpen):
        result = image

        # Step 1: Blur
        if blur_radius > 0:
            result = self.apply_blur(result, blur_radius)

        # Step 2: Brightness
        result = result * brightness

        # Step 3: Contrast
        mean = result.mean(dim=(1, 2), keepdim=True)
        result = (result - mean) * contrast + mean

        # Step 4: Sharpen
        if sharpen:
            result = self.apply_sharpen(result)

        return (torch.clamp(result, 0, 1),)

    def apply_blur(self, image, radius):
        # Apply Gaussian blur
        return image  # Placeholder

    def apply_sharpen(self, image):
        # Apply sharpening
        return image  # Placeholder
```

## Content-Hash Caching

Use MD5 hash of actual content to determine output filenames, enabling skip-if-identical behavior.

```python
import hashlib

class CachedEncoder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "fps": ("INT", {"default": 24}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "encode"
    CATEGORY = "video/encoding"

    def encode(self, images, fps):
        # Hash frame content at key indices
        m = hashlib.md5()
        b = images.shape[0]
        indices = [0, b // 2, b - 1]  # first, middle, last
        for idx in indices:
            m.update(images[idx].cpu().numpy().tobytes())
        m.update(str(fps).encode())
        uid = m.hexdigest()[:12]

        output_path = f"output/encoded_{uid}.mp4"

        # Skip if already exists
        import os
        if os.path.exists(output_path):
            return (output_path,)

        # Encode video
        self._encode_video(images, fps, output_path)
        return (output_path,)

    def _encode_video(self, images, fps, path):
        # ffmpeg encoding logic
        pass
```

## Parallel Encoding

Use ThreadPoolExecutor for concurrent video encoding.

```python
import threading
from concurrent.futures import ThreadPoolExecutor

class DualVideoEncoder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_1": ("IMAGE",),
                "video_2": ("IMAGE",),
                "fps": ("INT", {"default": 24}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    FUNCTION = "encode_both"
    CATEGORY = "video/encoding"

    def encode_both(self, video_1, video_2, fps):
        results = [None, None]

        def encode(idx, frames):
            results[idx] = self._encode(frames, fps)

        # Encode both videos in parallel
        t1 = threading.Thread(target=encode, args=(0, video_1))
        t2 = threading.Thread(target=encode, args=(1, video_2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        return (results[0], results[1])

    def _encode(self, frames, fps):
        # Write frames as PNGs in parallel, then ffmpeg
        import subprocess, tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            # Parallel PNG writes
            with ThreadPoolExecutor(max_workers=8) as pool:
                for i, frame in enumerate(frames):
                    pool.submit(self._save_frame, frame, os.path.join(tmpdir, f"f{i:06d}.png"))

            # Single ffmpeg invocation
            output = os.path.join(tmpdir, "out.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-framerate", str(fps),
                "-i", os.path.join(tmpdir, "f%06d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", output
            ], check=True, capture_output=True)
            return output

    def _save_frame(self, frame, path):
        from PIL import Image
        import numpy as np
        img = Image.fromarray((frame.cpu().numpy() * 255).astype(np.uint8))
        img.save(path)
```

## Config Hot-Reload

Re-read user configuration on every execution for live updates.

```python
import json
import os

class StyleSelector:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "styles.json")

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "style_name": (s._load_style_names(),),
            }
        }

    @classmethod
    def _load_style_names(cls):
        try:
            with open(cls.CONFIG_PATH, 'r') as f:
                styles = json.load(f)
            return list(styles.keys())
        except (FileNotFoundError, json.JSONDecodeError):
            return ["default"]

    RETURN_TYPES = ("STRING",)
    FUNCTION = "get_style"
    CATEGORY = "prompting"

    def get_style(self, style_name):
        # Re-read on every execution
        with open(self.CONFIG_PATH, 'r') as f:
            styles = json.load(f)
        return (styles.get(style_name, ""),)
```

## Global Patching

Scan all loaded modules to patch specific functions globally.

```python
import sys

class GlobalAttentionPatcher:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "patch_type": (["sa2", "sa3", "sdpa", "dynamic"],),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch_global"
    CATEGORY = "model/optimization"

    def patch_global(self, model, patch_type):
        model_clone = model.clone()

        # Scan all loaded modules for optimized_attention references
        patched_modules = []
        for name, module in sys.modules.items():
            if module is None:
                continue
            if hasattr(module, 'optimized_attention'):
                original = module.optimized_attention
                module.optimized_attention = self._create_patch(original, patch_type)
                patched_modules.append(name)

        print(f"[GlobalAttentionPatcher] Patched {len(patched_modules)} modules with {patch_type}")
        return (model_clone,)

    def _create_patch(self, original, patch_type):
        def patched(*args, **kwargs):
            # Apply patch logic
            return original(*args, **kwargs)
        return patched
```

## Template Tag System

Resolve `%NodeTitle.param%` syntax at runtime from the active prompt.

```python
class TemplateTextOverlay:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "template": ("STRING", {"multiline": True, "default": "Seed: %KSampler.seed%"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "overlay"
    CATEGORY = "image/text"

    def overlay(self, images, template, prompt=None, extra_pnginfo=None):
        resolved = self._resolve_template(template, prompt)
        # Apply text overlay with resolved values
        return (self._render_text(images, resolved),)

    def _resolve_template(self, template, prompt):
        import re
        if not prompt:
            return template

        def replace_match(match):
            node_title, param = match.group(1).split('.')
            # Find node by title in prompt
            for node_id, node_data in prompt.items():
                if node_data.get('_meta', {}).get('title') == node_title:
                    return str(node_data.get('inputs', {}).get(param, match.group(0)))
            return match.group(0)

        return re.sub(r'%([^%]+)%', replace_match, template)

    def _render_text(self, images, text):
        # Render text onto images
        return images
```

## Iterator Pattern

Counter that advances per queue run and auto-stops when exhausted.

```python
import random

class SamplerIterator:
    _counter = 0
    _total = 0

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "samplers": ("STRING", {"multiline": True, "default": "euler\neuler_ancestral\ndpmpp_2m"}),
                "max_iterations": ("INT", {"default": 0, "min": 0}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("sampler_name", "iteration")
    FUNCTION = "next"
    CATEGORY = "sampling/iterator"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Force re-execution every time
        return random.random()

    def next(self, samplers, max_iterations):
        sampler_list = [s.strip() for s in samplers.strip().split('\n') if s.strip()]
        self._total = max_iterations if max_iterations > 0 else len(sampler_list)

        current = self._counter % len(sampler_list)
        self._counter += 1

        return (sampler_list[current], current)
```

## Documentation Popup

JS extension that adds a "?" button to all nodes showing their DESCRIPTION as Markdown.

```javascript
// web/js/doc_popup.js
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "my.nodes.doc_popup",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (!nodeData.description) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const result = onNodeCreated?.apply(this, arguments);

            // Add "?" button
            const btn = document.createElement("button");
            btn.textContent = "?";
            btn.style.cssText = "position:absolute;top:2px;right:2px;width:20px;height:20px;border-radius:50%;background:orange;color:white;font-weight:bold;cursor:pointer;z-index:10;";
            btn.onclick = (e) => {
                e.stopPropagation();
                const popup = document.createElement("div");
                popup.style.cssText = "position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;color:#eee;padding:20px;border-radius:8px;max-width:600px;max-height:80vh;overflow:auto;z-index:1000;white-space:pre-wrap;";
                popup.innerHTML = nodeData.description;
                const close = document.createElement("button");
                close.textContent = "X";
                close.style.cssText = "position:absolute;top:5px;right:10px;background:none;border:none;color:white;font-size:16px;cursor:pointer;";
                close.onclick = () => popup.remove();
                popup.appendChild(close);
                document.body.appendChild(popup);
            };
            this.addDOMWidget("doc_btn", "button", btn);

            return result;
        };
    }
});
```

## Dynamic Return Types Proxy

Proxy class that reads types at access time instead of import time.

```python
class _DynamicReturnTypes:
    """Proxy that reads type lists at access time, not import time."""
    def __init__(self, base_list):
        self._base = base_list

    def __getitem__(self, key):
        return self._base[key]

    def __iter__(self):
        return iter(self._base)

    def __len__(self):
        return len(self._base)

class DynamicSamplerNode:
    # Use proxy so SAMPLERS list is read at runtime, not import time
    RETURN_TYPES = _DynamicReturnTypes(["COMBO"] + ["STRING"] * 10)

    @classmethod
    def INPUT_TYPES(s):
        from comfy.samplers import KSampler
        return {
            "required": {
                "sampler_name": (KSampler.SAMPLERS,),
                "scheduler": (KSampler.SCHEDULERS,),
            }
        }
```

## WebSocket Real-Time Updates

Push real-time status updates from server to client.

```python
# Server side (Python)
from server import PromptServer

class StatusNode:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"model": ("MODEL",)}}

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "process"
    CATEGORY = "model/optimization"
    OUTPUT_NODE = True

    def process(self, model):
        # Send real-time update to client
        PromptServer.instance.send_sync("my/status_update", {
            "status": "processing",
            "progress": 0.5,
            "message": "Applying optimization..."
        })

        # Process...
        result = self._optimize(model)

        PromptServer.instance.send_sync("my/status_update", {
            "status": "complete",
            "progress": 1.0,
            "message": "Done!"
        })

        return (result,)
```

```javascript
// Client side (JS)
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "my.status_display",
    async setup() {
        app.api.addEventListener("my/status_update", (event) => {
            const { status, progress, message } = event.detail;
            console.log(`Status: ${status} - ${message} (${progress * 100}%)`);
        });
    }
});
```

## Font Bundling

Ship fonts with cross-platform fallback chain.

```python
import os

class TextRenderer:
    FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

    @classmethod
    def INPUT_TYPES(s):
        fonts = ["BundledSans.ttf", "BundledMono.ttf"]
        # Add system fonts as fallback
        system_fonts = self._get_system_fonts()
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "font": (fonts + system_fonts,),
                "size": ("INT", {"default": 24, "min": 8, "max": 200}),
            }
        }

    def _get_system_fonts(self):
        import platform
        system = platform.system()
        if system == "Darwin":
            return ["/System/Library/Fonts/Helvetica.ttc"]
        elif system == "Windows":
            return ["C:/Windows/Fonts/arial.ttf"]
        else:
            return ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

    def _load_font(self, font_name, size):
        from PIL import ImageFont
        # Try bundled first
        bundled = os.path.join(self.FONT_DIR, font_name)
        if os.path.exists(bundled):
            return ImageFont.truetype(bundled, size)
        # Fallback to system
        return ImageFont.truetype(font_name, size)
```
