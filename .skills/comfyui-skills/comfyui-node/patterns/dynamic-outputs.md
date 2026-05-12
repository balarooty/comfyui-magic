# Dynamic Outputs Node Pattern

## When to Use

Use this pattern when the number of outputs must be determined at runtime based on input parameters or data. The `IS_DYNAMIC` classmethod signals to ComfyUI that output types/names are computed dynamically. This is essential for nodes like splitters, unpackers, or routers where the output count varies.

**Typical use cases:**
- Splitting an image batch into individual images
- Splitting a string into multiple parts
- Unpacking a list into individual elements
- Routing inputs to N outputs
- Extracting specific channels or features

## Architecture

```
INPUT (with N parameter) → IS_DYNAMIC() → get_output_types() → get_output_names()
                              ↓                    ↓                   ↓
                    marks node as dynamic    compute types      compute names
                              ↓
                    execute() → return tuple of N outputs
```

## Key Components

| Component | Purpose |
|---|---|
| `IS_DYNAMIC()` | Classmethod returning `True` — marks this node as having dynamic outputs |
| `get_output_types(**kwargs)` | Classmethod returning tuple of output type strings |
| `get_output_names(**kwargs)` | Classmethod returning tuple of output name strings |
| `dynamic=True` | Input parameter flag allowing dynamic value ranges |
| `get_input_info(**kwargs)` | Optional classmethod for dynamic input configuration |

## Complete Code Example

```python
import torch

class ImageBatchSplitter:
    """Splits an image batch into individual images."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "count": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "dynamic": True,
                    "tooltip": "Number of output images to split into"
                }),
            }
        }

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, images=None, count=4, **kwargs):
        # Return one IMAGE output for each split
        return ("IMAGE",) * count

    @classmethod
    def get_output_names(cls, images=None, count=4, **kwargs):
        return tuple(f"image_{i}" for i in range(count))

    FUNCTION = "split"
    CATEGORY = "image/batch"

    def split(self, images, count):
        B = images.shape[0]
        results = []

        for i in range(count):
            if i < B:
                # Return individual image [1, H, W, C]
                results.append(images[i:i+1])
            else:
                # Not enough images in batch — return blank
                H, W, C = images.shape[1], images.shape[2], images.shape[3]
                blank = torch.zeros(1, H, W, C, device=images.device, dtype=images.dtype)
                results.append(blank)

        return tuple(results)
```

## IS_DYNAMIC() Deep Dive

When `IS_DYNAMIC()` returns `True`, ComfyUI:

1. Calls `get_output_types(**kwargs)` to determine output types before execution
2. Calls `get_output_names(**kwargs)` to determine output names
3. Dynamically generates the node's output slots in the UI
4. Calls `execute()` which must return a tuple matching the declared types

```python
# ComfyUI's internal handling (simplified):
if node.IS_DYNAMIC():
    output_types = node.get_output_types(**inputs)
    output_names = node.get_output_names(**inputs)
    # Create len(output_types) output slots
    # Execute and verify returned tuple matches
```

## Key Considerations

1. **Return tuple length must match.** If `get_output_types` returns 5 types, `execute` must return exactly 5 values. Mismatches cause errors.

2. **`dynamic=True` on inputs.** Mark inputs that affect output count with `"dynamic": True`. This tells ComfyUI to re-evaluate outputs when the value changes.

3. **get_output_types receives resolved inputs.** The kwargs contain the actual input values (after type resolution), not the input definitions.

4. **Performance consideration.** `get_output_types` and `get_output_names` are called frequently (for UI updates). Keep them fast — no heavy computation.

5. **Max output limit.** While there's no hard limit, very large output counts (>100) may degrade UI performance. Consider a reasonable maximum.

6. **Empty outputs.** If the batch is smaller than `count`, return zero-filled tensors rather than `None` to avoid downstream errors.

7. **Type consistency.** All outputs don't need to be the same type. You can mix IMAGE, MASK, STRING, etc. based on the data.

## Variations

### String Splitter

```python
class StringSplitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "delimiter": ("STRING", {"default": "\n"}),
                "max_splits": ("INT", {"default": 10, "min": 1, "max": 100, "dynamic": True}),
            }
        }

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, text="", delimiter="\n", max_splits=10, **kwargs):
        parts = text.split(delimiter, max_splits - 1) if text else [""]
        count = len(parts)
        return ("STRING",) * count

    @classmethod
    def get_output_names(cls, text="", delimiter="\n", max_splits=10, **kwargs):
        parts = text.split(delimiter, max_splits - 1) if text else [""]
        return tuple(f"part_{i}" for i in range(len(parts)))

    FUNCTION = "split"
    CATEGORY = "utils/text"

    def split(self, text, delimiter, max_splits):
        if not text:
            return ("",)
        parts = text.split(delimiter, max_splits - 1)
        return tuple(parts)
```

### Multi-Type Router

```python
class DataRouter:
    """Routes different data types to numbered outputs."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "route_count": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 10,
                    "dynamic": True
                }),
            },
            "optional": {
                "text": ("STRING",),
            }
        }

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, image=None, mask=None, route_count=2, text=None, **kwargs):
        types = []
        for i in range(route_count):
            if i == 0:
                types.append("IMAGE")
            elif i == 1:
                types.append("MASK")
            else:
                types.append("STRING")
        return tuple(types)

    @classmethod
    def get_output_names(cls, route_count=2, **kwargs):
        names = []
        for i in range(route_count):
            if i == 0:
                names.append("image")
            elif i == 1:
                names.append("mask")
            else:
                names.append(f"text_{i-2}")
        return tuple(names)

    FUNCTION = "route"
    CATEGORY = "utils/routing"

    def route(self, image, mask, route_count, text=""):
        results = []
        for i in range(route_count):
            if i == 0:
                results.append(image)
            elif i == 1:
                results.append(mask)
            else:
                results.append(text)
        return tuple(results)
```

### Batch Distributor

```python
class BatchDistributor:
    """Distributes a batch of images across outputs evenly."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "outputs": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 32,
                    "dynamic": True
                }),
                "strategy": (["sequential", "interleaved"],),
            }
        }

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, images=None, outputs=4, **kwargs):
        return ("IMAGE",) * outputs

    @classmethod
    def get_output_names(cls, images=None, outputs=4, **kwargs):
        return tuple(f"batch_{i}" for i in range(outputs))

    FUNCTION = "distribute"
    CATEGORY = "image/batch"

    def distribute(self, images, outputs, strategy):
        B = images.shape[0]
        results = []

        if strategy == "sequential":
            # Split batch sequentially across outputs
            chunk_size = max(1, B // outputs)
            for i in range(outputs):
                start = i * chunk_size
                end = start + chunk_size if i < outputs - 1 else B
                if start < B:
                    results.append(images[start:end])
                else:
                    H, W, C = images.shape[1], images.shape[2], images.shape[3]
                    results.append(torch.zeros(1, H, W, C, device=images.device, dtype=images.dtype))
        else:
            # Interleaved: image 0 → out 0, image 1 → out 1, ...
            for i in range(outputs):
                indices = list(range(i, B, outputs))
                if indices:
                    results.append(images[indices])
                else:
                    H, W, C = images.shape[1], images.shape[2], images.shape[3]
                    results.append(torch.zeros(1, H, W, C, device=images.device, dtype=images.dtype))

        return tuple(results)
```

### Category Extractor

```python
class MaskCategoryExtractor:
    """Extracts individual mask categories from a segmentation mask."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
                "num_categories": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 20,
                    "dynamic": True
                }),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, mask=None, num_categories=3, **kwargs):
        return ("MASK",) * num_categories

    @classmethod
    def get_output_names(cls, mask=None, num_categories=3, **kwargs):
        return tuple(f"category_{i}" for i in range(num_categories))

    FUNCTION = "extract"
    CATEGORY = "mask/segmentation"

    def extract(self, mask, num_categories, threshold):
        # mask: [B, H, W]
        B, H, W = mask.shape
        results = []

        # Divide mask intensity into N categories
        for i in range(num_categories):
            low = i / num_categories
            high = (i + 1) / num_categories
            category_mask = ((mask >= low) & (mask < high)).float()
            results.append(category_mask)

        return tuple(results)
```

### Dynamic Input Count

```python
class DynamicInputCombiner:
    """Combines N inputs into a list. Uses get_input_info for dynamic inputs."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "count": ("INT", {"default": 2, "min": 1, "max": 10, "dynamic": True}),
            },
            "optional": {
                "image_0": ("IMAGE",),
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "image_5": ("IMAGE",),
                "image_6": ("IMAGE",),
                "image_7": ("IMAGE",),
                "image_8": ("IMAGE",),
                "image_9": ("IMAGE",),
            }
        }

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, count=2, **kwargs):
        return ("IMAGE",)

    @classmethod
    def get_output_names(cls, count=2, **kwargs):
        return ("images",)

    FUNCTION = "combine"
    CATEGORY = "image/batch"

    def combine(self, count, **kwargs):
        images = []
        for i in range(count):
            key = f"image_{i}"
            if key in kwargs and kwargs[key] is not None:
                images.append(kwargs[key])

        if not images:
            raise ValueError("At least one image input must be connected")

        # Concatenate along batch dimension
        return (torch.cat(images, dim=0),)
```
