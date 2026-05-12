# Output Types Reference

How ComfyUI node outputs work, type matching, and output patterns.

## Output Type Strings

Output types use the same string identifiers as input types. The type string determines which input ports can connect.

```python
RETURN_TYPES = ("IMAGE", "MASK", "STRING", "FLOAT", "INT", "BOOLEAN")
RETURN_NAMES = ("image", "mask", "info", "value", "count", "enabled")
```

## Common Output Types

### Primitive Outputs

```python
RETURN_TYPES = ("INT",)        # Integer value
RETURN_TYPES = ("FLOAT",)      # Float value
RETURN_TYPES = ("STRING",)     # Text string
RETURN_TYPES = ("BOOLEAN",)    # True/False
```

### Tensor Outputs

```python
RETURN_TYPES = ("IMAGE",)      # Image tensor [B, H, W, C]
RETURN_TYPES = ("LATENT",)     # Latent tensor [B, C, H, W]
RETURN_TYPES = ("MASK",)       # Mask tensor [B, H, W]
RETURN_TYPES = ("AUDIO",)      # Audio waveform tensor
```

### Model Outputs

```python
RETURN_TYPES = ("MODEL",)      # Diffusion model
RETURN_TYPES = ("CLIP",)       # CLIP encoder
RETURN_TYPES = ("VAE",)        # VAE model
RETURN_TYPES = ("CONDITIONING",)  # Conditioning data
```

### Sampling Outputs

```python
RETURN_TYPES = ("NOISE",)      # Noise generator
RETURN_TYPES = ("SAMPLER",)    # Sampler algorithm
RETURN_TYPES = ("SIGMAS",)     # Sigma schedule
RETURN_TYPES = ("GUIDER",)     # Guidance strategy
```

## How Outputs Connect

Outputs connect to inputs of the same type. The connection is type-checked at workflow load time.

```python
# Node A produces IMAGE
class NodeA:
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"

    def generate(self):
        return (image_tensor,)

# Node B accepts IMAGE
class NodeB:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"image": ("IMAGE",)}}

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"

    def process(self, image):
        return (processed_image,)
```

## Multiple Outputs

Return a tuple with values in the same order as RETURN_TYPES.

```python
class SplitImage:
    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("image", "alpha_mask", "info")
    FUNCTION = "split"

    def split(self, image):
        if image.shape[-1] == 4:
            rgb = image[:, :, :, :3]
            alpha = image[:, :, :, 3]
            info = "RGBA image split"
        else:
            rgb = image
            alpha = torch.ones(image.shape[:3])
            info = "RGB image (no alpha)"

        return (rgb, alpha, info)
```

## RETURN_NAMES

Optional human-readable names for outputs. Displayed in the UI instead of type strings.

```python
RETURN_TYPES = ("IMAGE", "MASK", "FLOAT")
RETURN_NAMES = ("processed_image", "edge_mask", "confidence_score")
```

## OUTPUT_IS_LIST

Tuple of booleans indicating which outputs are lists. Used when a node produces multiple items that should be processed individually downstream.

```python
class BatchSplitter:
    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("first_half", "second_half")
    OUTPUT_IS_LIST = (True, True)  # Both outputs are lists
    FUNCTION = "split"

    def split(self, images):
        mid = len(images) // 2
        return (images[:mid], images[mid:])
```

### How OUTPUT_IS_LIST Works

When `OUTPUT_IS_LIST[i]` is `True`, the corresponding output is expected to be a Python list. Downstream nodes with `INPUT_IS_LIST = True` will receive the list directly.

```python
# Producer node
class ImageSequence:
    RETURN_TYPES = ("IMAGE",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "generate"

    def generate(self, count):
        return ([generate_image(i) for i in range(count)],)

# Consumer node
class ProcessBatch:
    INPUT_IS_LIST = True
    FUNCTION = "process"

    def process(self, images):
        # images is a list of IMAGE tensors
        return ([self.enhance(img) for img in images],)
```

## OUTPUT_NODE

Marks a node as a terminal/output node. These nodes don't need downstream connections and can display results.

```python
class SaveImage:
    OUTPUT_NODE = True
    FUNCTION = "save"

    def save(self, image, filename_prefix):
        # Save logic...
        return ()
```

### Output Nodes with UI Data

Output nodes can return UI data for display in the frontend.

```python
class PreviewImage:
    OUTPUT_NODE = True
    FUNCTION = "preview"

    def preview(self, image):
        # Process image for display
        results = []
        for img in image:
            # Save temp file or prepare for display
            results.append({"filename": temp_path, "subfolder": "", "type": "temp"})

        return {"ui": {"images": results}}
```

## Custom Output Types

Any uppercase string can be a custom type. Must match between producer and consumer nodes.

```python
# Producer
class StyleExtractor:
    RETURN_TYPES = ("STYLE_DATA", "STYLE_NAME")
    FUNCTION = "extract"

    def extract(self, image):
        style_data = analyze_style(image)
        style_name = classify_style(style_data)
        return (style_data, style_name)

# Consumer
class StyleApplier:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "style": ("STYLE_DATA",),
                "target": ("IMAGE",),
            }
        }

    FUNCTION = "apply"

    def apply(self, style, target):
        return (apply_style(target, style),)
```

## Dynamic Outputs

For nodes that produce a variable number of outputs, use `IS_DYNAMIC`, `get_output_types`, and `get_output_names`.

```python
class DynamicSplitter:
    RETURN_TYPES = tuple(["IMAGE"] * 50)  # Maximum possible
    FUNCTION = "split"

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

## Output Type Compatibility

Types are matched by exact string comparison. There is no inheritance or coercion.

```python
# These are different types — cannot connect
("IMAGE",)      # image tensor
("LATENT",)     # latent tensor
("MASK",)       # mask tensor

# Even though they're all tensors, they're not interchangeable
# Use conversion nodes to transform between types
```

### Type Conversion Pattern

Create explicit conversion nodes when types need to change.

```python
class MaskToImage:
    """Converts a mask tensor to an image tensor."""
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "convert"

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"mask": ("MASK",)}}

    def convert(self, mask):
        # Expand mask [B, H, W] to image [B, H, W, 3]
        return (mask.unsqueeze(-1).repeat(1, 1, 1, 3),)

class ImageToMask:
    """Converts an image to a mask using luminance."""
    RETURN_TYPES = ("MASK",)
    FUNCTION = "convert"

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"image": ("IMAGE",)}}

    def convert(self, image):
        # Convert to grayscale
        gray = image[:, :, :, 0] * 0.299 + image[:, :, :, 1] * 0.587 + image[:, :, :, 2] * 0.114
        return (gray,)
```

## Complete Example: Multi-Output Node

```python
class ImageAnalysis:
    """Analyzes an image and returns multiple metrics."""

    RETURN_TYPES = ("IMAGE", "FLOAT", "FLOAT", "FLOAT", "STRING")
    RETURN_NAMES = ("image", "brightness", "contrast", "sharpness", "summary")
    FUNCTION = "analyze"
    CATEGORY = "image/analysis"
    DESCRIPTION = "Analyzes image properties and returns metrics"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
            },
        }

    def analyze(self, image):
        # Calculate brightness
        brightness = image.mean().item()

        # Calculate contrast
        contrast = image.std().item()

        # Calculate sharpness (Laplacian variance)
        gray = image.mean(dim=-1, keepdim=True)
        laplacian_kernel = torch.tensor([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=torch.float32)
        laplacian_kernel = laplacian_kernel.view(1, 1, 3, 3)
        if gray.dim() == 3:
            gray = gray.unsqueeze(0)
        lap = torch.nn.functional.conv2d(gray.permute(0, 3, 1, 2), laplacian_kernel, padding=1)
        sharpness = lap.var().item()

        summary = f"Brightness: {brightness:.2f}, Contrast: {contrast:.2f}, Sharpness: {sharpness:.2f}"

        return (image, brightness, contrast, sharpness, summary)
```
