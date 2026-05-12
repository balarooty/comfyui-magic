# Image Processor Node Pattern

## When to Use

Use this pattern for nodes that process images as tensors — applying filters, transformations, color adjustments, compositing, or any pixel-level operation. This pattern handles ComfyUI's image tensor format, batch processing, and optional mask integration.

## Anatomy

```
IMAGE tensor   → [B, H, W, C] float32 in range [0, 1]
MASK tensor    → [B, H, W] float32 in range [0, 1] (white = affected)
torch ops      → vectorized operations on GPU/CPU tensors
batch loop     → iterate over batch dimension when per-image logic is needed
```

## Complete Code Example: Image Blur with Mask Support

```python
import torch
import torch.nn.functional as F

class ImageBlurWithMask:
    """Applies Gaussian blur to an image, optionally constrained by a mask."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "radius_x": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 128,
                    "step": 1,
                    "tooltip": "Horizontal blur radius."
                }),
                "radius_y": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 128,
                    "step": 1,
                    "tooltip": "Vertical blur radius."
                }),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "blur_image"
    CATEGORY = "image/blur"

    def blur_image(self, image, radius_x, radius_y, mask=None):
        # image shape: [B, H, W, C], values in [0, 1]
        # mask shape: [B, H, W], values in [0, 1]

        B, H, W, C = image.shape

        # Convert from [B, H, W, C] to [B, C, H, W] for conv2d
        img = image.permute(0, 3, 1, 2)

        # Build a Gaussian kernel
        kernel_x = self._gaussian_kernel(radius_x).to(img.device, img.dtype)
        kernel_y = self._gaussian_kernel(radius_y).to(img.device, img.dtype)

        # Apply separable Gaussian blur (horizontal then vertical)
        # Pad to keep spatial dimensions
        img = F.pad(img, (radius_x, radius_x, 0, 0), mode="reflect")
        img = F.conv2d(img, kernel_x, groups=C)

        img = F.pad(img, (0, 0, radius_y, radius_y), mode="reflect")
        img = F.conv2d(img, kernel_y, groups=C)

        # Convert back to [B, H, W, C]
        result = img.permute(0, 2, 3, 1)

        # If mask is provided, blend original and blurred using the mask
        if mask is not None:
            # mask: [B, H, W] → [B, H, W, 1] for broadcasting
            mask_expanded = mask.unsqueeze(-1)
            result = image * (1.0 - mask_expanded) + result * mask_expanded

        result = torch.clamp(result, 0.0, 1.0)
        return (result,)

    @staticmethod
    def _gaussian_kernel(radius):
        """Creates a 1D Gaussian kernel of size (2*radius + 1)."""
        size = 2 * radius + 1
        x = torch.arange(size, dtype=torch.float32) - radius
        kernel = torch.exp(-0.5 * (x / max(radius / 3.0, 1.0)) ** 2)
        kernel = kernel / kernel.sum()

        # Reshape for conv2d: [out_channels, in_channels/groups, kernel_h, kernel_w]
        return kernel.view(1, 1, 1, -1)

NODE_CLASS_MAPPINGS = {
    "ImageBlurWithMask": ImageBlurWithMask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageBlurWithMask": "Image Blur (Masked)",
}
```

## Key Considerations

### IMAGE Tensor Format
- Shape: `[B, H, W, C]` — batch, height, width, channels.
- Dtype: `float32`.
- Range: `[0.0, 1.0]`. Values outside this range are clipped on output.
- For convolution operations (torch.nn.functional), convert to `[B, C, H, W]` with `.permute(0, 3, 1, 2)`.

### MASK Tensor Format
- Shape: `[B, H, W]` — same batch and spatial dimensions as the image.
- Range: `[0.0, 1.0]` where `1.0` = fully affected, `0.0` = untouched.
- Use `.unsqueeze(-1)` to expand to `[B, H, W, 1]` for broadcasting with images.

### Batch Processing
- Most `torch` operations are batch-native — they apply to all images in the batch simultaneously.
- Only use a per-image loop when the operation has image-dependent control flow (e.g., adaptive thresholds).
- When looping, pre-allocate the output tensor for performance:

```python
results = torch.empty_like(image)
for i in range(B):
    results[i] = process_single(image[i])
```

### Memory Efficiency
- Avoid creating unnecessary copies. Use in-place operations (`.mul_()`, `.add_()`) when possible.
- For large images, consider processing in patches or downsampling.
- Always `.clamp(0, 1)` the output to prevent downstream issues.

### Device Handling
- Input tensors may be on CPU or GPU. Operations automatically match the input device.
- When creating new tensors (e.g., kernels), use `.to(device, dtype)` to match the input.

## Variations

### Color Space Conversion

```python
def rgb_to_hsv(self, image):
    # image: [B, H, W, 3]
    r, g, b = image[..., 0], image[..., 1], image[..., 2]
    max_c = torch.max(image[..., :3], dim=-1).values
    min_c = torch.min(image[..., :3], dim=-1).values
    diff = max_c - min_c

    # Saturation
    s = torch.where(max_c > 0, diff / max_c, torch.zeros_like(max_c))

    # Value
    v = max_c

    # Hue
    h = torch.where(
        diff > 0,
        torch.where(
            max_c == r, ((g - b) / diff) % 6,
            torch.where(max_c == g, (b - r) / diff + 2, (r - g) / diff + 4)
        ) / 6.0,
        torch.zeros_like(diff)
    )

    return (torch.stack([h, s, v], dim=-1),)
```

### Image Resize with Batch

```python
def resize_batch(self, image, width, height):
    # image: [B, H, W, C]
    img = image.permute(0, 3, 1, 2)  # [B, C, H, W]
    resized = F.interpolate(img, size=(height, width), mode="bilinear", align_corners=False)
    return (resized.permute(0, 2, 3, 1),)  # [B, H, W, C]
```

### Mask-Based Region Processing

```python
def process_region(self, image, mask, process_fn):
    processed = process_fn(image)
    mask_3d = mask.unsqueeze(-1)  # [B, H, W, 1]
    result = image * (1.0 - mask_3d) + processed * mask_3d
    return (torch.clamp(result, 0.0, 1.0),)
```

### Alpha Compositing

```python
def composite_over(self, foreground, background, alpha):
    # alpha: [B, H, W, 1] or [B, H, W]
    if alpha.dim() == 3:
        alpha = alpha.unsqueeze(-1)
    result = foreground * alpha + background * (1.0 - alpha)
    return (torch.clamp(result, 0.0, 1.0),)
```
