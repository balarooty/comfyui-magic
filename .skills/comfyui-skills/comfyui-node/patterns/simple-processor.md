# Simple Processor Node Pattern

## When to Use

Use this pattern for nodes that take an input, apply a transformation, and return an output. This is the most fundamental node pattern — ideal for image adjustments, tensor math, string manipulation, or any stateless operation.

## Anatomy

```
INPUT_TYPES (classmethod) → defines inputs and their types
RETURN_TYPES             → declares output types
FUNCTION                 → name of the method that executes the logic
CATEGORY                 → UI folder placement
```

## Complete Code Example: Image Brightness Adjustment

```python
import torch

class ImageBrightness:
    """Adjusts the brightness of an image by multiplying pixel values."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "brightness": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 5.0,
                    "step": 0.01,
                    "display": "slider"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "adjust_brightness"
    CATEGORY = "image/adjustments"

    def adjust_brightness(self, image, brightness):
        # image shape: [B, H, W, C] with values in [0, 1]
        result = image * brightness
        result = torch.clamp(result, 0.0, 1.0)
        return (result,)

NODE_CLASS_MAPPINGS = {
    "ImageBrightness": ImageBrightness,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageBrightness": "Image Brightness",
}
```

## Key Considerations

### Input Declaration
- `"required"` inputs must be connected or have a default value.
- `"optional"` inputs can be left unconnected (the function receives `None` or the default).
- `"hidden"` inputs are populated by the system (e.g., `prompt`, `extra_pnginfo`, `unique_id`).

### Return Convention
- `RETURN_TYPES` is always a tuple of strings, even for a single output.
- The execution method must return a **tuple** matching `RETURN_TYPES` in order and count.
- Use `RETURN_NAMES` to give descriptive labels to outputs in the UI.

### Type Annotations
- `"FLOAT"` supports `min`, `max`, `step`, and `"display": "slider"`.
- `"INT"` supports the same widget options.
- `"STRING"` can use `"multiline": True` for large text fields.
- `"BOOLEAN"` renders as a checkbox.

### No Side Effects
- Simple processors should be pure functions — same inputs always produce the same outputs.
- Avoid writing files or modifying global state inside the processing method.

## Variations

### Multi-Input Processor

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "image_a": ("IMAGE",),
            "image_b": ("IMAGE",),
            "blend": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
        },
    }

RETURN_TYPES = ("IMAGE",)
FUNCTION = "blend_images"
CATEGORY = "image/compositing"

def blend_images(self, image_a, image_b, blend):
    result = image_a * (1.0 - blend) + image_b * blend
    return (torch.clamp(result, 0.0, 1.0),)
```

### Optional Input Processor

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "image": ("IMAGE",),
        },
        "optional": {
            "mask": ("MASK",),
            "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0}),
        },
    }

def process(self, image, mask=None, strength=1.0):
    if mask is not None:
        # Apply mask logic
        pass
    return (result,)
```

### String Processor

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "text": ("STRING", {"multiline": True, "default": ""}),
            "prefix": ("STRING", {"default": ""}),
        },
    }

RETURN_TYPES = ("STRING",)
FUNCTION = "process_text"
CATEGORY = "text"

def process_text(self, text, prefix):
    return (prefix + text,)
```
