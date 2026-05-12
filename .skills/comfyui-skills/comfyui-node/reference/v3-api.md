# v3 io.ComfyNode API Reference

The modern, typed node API introduced in ComfyUI v3. Uses declarative schemas and explicit typing. Less widely adopted than Legacy but provides better type safety and cleaner structure.

## Import

```python
from comfy_api.latest import io
```

## Class Structure

Nodes inherit from `io.ComfyNode` and define a schema via `define_schema()`.

```python
from comfy_api.latest import io

class MyNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="my_node",
            display_name="My Node",
            category="image/processing",
            description="Does something useful",
            search_aliases=["alias1", "alias2"],
            is_experimental=False,
            inputs=[...],
            outputs=[...],
        )

    @classmethod
    def execute(cls, **kwargs) -> io.NodeOutput:
        ...
        return io.NodeOutput(result)
```

## io.Schema Parameters

```python
io.Schema(
    node_id="my_node",                    # Unique identifier string
    display_name="My Node",               # UI display name
    category="image/processing",          # Menu category path
    description="What this node does",    # Tooltip description
    search_aliases=["blur", "smooth"],    # Extra search terms
    is_experimental=False,                 # Mark as experimental
    inputs=[...],                         # List of input definitions
    outputs=[...],                        # List of output definitions
)
```

## Input Types

Typed input constructors. Each returns an input definition for use in `io.Schema(inputs=[...])`.

### Image Input

```python
io.Image.Input(
    name="image",
    tooltip="Input image tensor",
    optional=False,
    lazy=False,
)
```

### Float Input

```python
io.Float.Input(
    name="strength",
    tooltip="Blend strength",
    default=1.0,
    min=0.0,
    max=1.0,
    step=0.01,
    optional=False,
    lazy=False,
)
```

### Int Input

```python
io.Int.Input(
    name="seed",
    tooltip="Random seed",
    default=0,
    min=0,
    max=0xFFFFFFFFFFFFFFFF,
    step=1,
    optional=False,
    lazy=False,
)
```

### Boolean Input

```python
io.Boolean.Input(
    name="enabled",
    tooltip="Enable processing",
    default=True,
    optional=False,
    lazy=False,
)
```

### String Input

```python
io.String.Input(
    name="prompt",
    tooltip="Text prompt",
    default="",
    multiline=True,
    placeholder="Enter your prompt...",
    optional=False,
    lazy=False,
)
```

### Combo Input

```python
io.Combo.Input(
    name="mode",
    tooltip="Processing mode",
    options=["fast", "quality", "balanced"],
    optional=False,
    lazy=False,
)
```

### Model Inputs

```python
io.Model.Input(name="model", optional=False, lazy=False)
io.Clip.Input(name="clip", optional=False, lazy=False)
io.Vae.Input(name="vae", optional=False, lazy=False)
io.Latent.Input(name="latent", optional=False, lazy=False)
io.Conditioning.Input(name="conditioning", optional=False, lazy=False)
io.Mask.Input(name="mask", optional=True, lazy=False)
io.Audio.Input(name="audio", optional=False, lazy=False)
```

### Input Parameters

All input types share these common parameters:

| Parameter   | Type    | Description                                      |
|-------------|---------|--------------------------------------------------|
| `name`      | str     | Input name (used as kwarg in execute)            |
| `tooltip`   | str     | Hover tooltip text                               |
| `default`   | any     | Default value when unconnected                   |
| `min`       | number  | Minimum value (numeric types only)               |
| `max`       | number  | Maximum value (numeric types only)               |
| `step`      | number  | Step increment (numeric types only)              |
| `multiline` | bool    | Multi-line text input (String only)              |
| `optional`  | bool    | Whether connection is required                   |
| `lazy`      | bool    | Defer evaluation until value needed              |

## Output Types

Typed output constructors for use in `io.Schema(outputs=[...])`.

```python
io.Image.Output(name="image", tooltip="Processed image")
io.Float.Output(name="value", tooltip="Computed value")
io.Model.Output(name="model", tooltip="Modified model")
io.Clip.Output(name="clip")
io.Vae.Output(name="vae")
io.Latent.Output(name="latent")
io.Conditioning.Output(name="conditioning")
io.Mask.Output(name="mask")
io.Audio.Output(name="audio")
```

## execute() Classmethod

The main logic method. Returns `io.NodeOutput` with results.

```python
@classmethod
def execute(cls, image, strength, mask=None) -> io.NodeOutput:
    result = image * strength
    if mask is not None:
        result = result * mask
    return io.NodeOutput(result)
```

### Multiple Outputs

Return multiple values in order matching `outputs` in the schema.

```python
@classmethod
def execute(cls, image, mask) -> io.NodeOutput:
    processed = image * mask
    inverted_mask = 1.0 - mask
    return io.NodeOutput(processed, inverted_mask)
```

### UI Output

Include UI data for terminal/output nodes.

```python
@classmethod
def execute(cls, image) -> io.NodeOutput:
    # Save image...
    return io.NodeOutput(ui={"images": [saved_path]})
```

## Lazy Evaluation

Inputs marked `lazy=True` are only evaluated when accessed. Useful for expensive computations that may not be needed.

```python
@classmethod
def define_schema(cls):
    return io.Schema(
        node_id="conditional_node",
        display_name="Conditional Node",
        category="utility",
        description="Only evaluates expensive input when needed",
        inputs=[
            io.Image.Input(name="image"),
            io.Boolean.Input(name="use_enhancement", default=False),
            io.Image.Input(name="enhancement_source", lazy=True, optional=True),
        ],
        outputs=[
            io.Image.Output(name="result"),
        ],
    )

@classmethod
def execute(cls, image, use_enhancement, enhancement_source=None) -> io.NodeOutput:
    if use_enhancement:
        # enhancement_source is only evaluated here
        enhanced = enhancement_source()
        return io.NodeOutput(enhanced)
    return io.NodeOutput(image)
```

## ComfyExtension Class

For registering v3 nodes with ComfyUI's extension system.

```python
from comfy_api.latest import io

class MyExtension(io.ComfyExtension):
    @classmethod
    def get_node_list(cls):
        return [MyNode, AnotherNode]

def comfy_entrypoint():
    return MyExtension
```

## Complete Example

```python
from comfy_api.latest import io
import torch

class ImageAdjust(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="image_adjust",
            display_name="Image Adjust",
            category="image/adjustment",
            description="Adjust image brightness, contrast, and saturation",
            search_aliases=["brightness", "contrast", "saturation", "color"],
            is_experimental=False,
            inputs=[
                io.Image.Input(name="image", tooltip="Input image"),
                io.Float.Input(
                    name="brightness",
                    tooltip="Brightness multiplier",
                    default=1.0,
                    min=0.0,
                    max=3.0,
                    step=0.01,
                ),
                io.Float.Input(
                    name="contrast",
                    tooltip="Contrast multiplier",
                    default=1.0,
                    min=0.0,
                    max=3.0,
                    step=0.01,
                ),
                io.Float.Input(
                    name="saturation",
                    tooltip="Saturation multiplier",
                    default=1.0,
                    min=0.0,
                    max=3.0,
                    step=0.01,
                ),
                io.Boolean.Input(
                    name="clamp",
                    tooltip="Clamp output to [0, 1]",
                    default=True,
                ),
            ],
            outputs=[
                io.Image.Output(name="image", tooltip="Adjusted image"),
            ],
        )

    @classmethod
    def execute(cls, image, brightness, contrast, saturation, clamp) -> io.NodeOutput:
        # Brightness
        result = image * brightness

        # Contrast
        mean = result.mean(dim=(1, 2), keepdim=True)
        result = (result - mean) * contrast + mean

        # Saturation
        gray = result.mean(dim=-1, keepdim=True)
        result = gray + (result - gray) * saturation

        if clamp:
            result = torch.clamp(result, 0.0, 1.0)

        return io.NodeOutput(result)


class AdjustExtension(io.ComfyExtension):
    @classmethod
    def get_node_list(cls):
        return [ImageAdjust]


def comfy_entrypoint():
    return AdjustExtension
```

## v3 vs Legacy Comparison

| Feature               | Legacy v1               | v3 io.ComfyNode          |
|-----------------------|-------------------------|---------------------------|
| Base class            | None (plain class)      | `io.ComfyNode`           |
| Schema definition     | `INPUT_TYPES` + attrs   | `define_schema()`        |
| Type safety           | String-based            | Typed constructors       |
| Execute method        | Instance method          | Classmethod              |
| Return type           | Plain tuple             | `io.NodeOutput`          |
| Registration          | `NODE_CLASS_MAPPINGS`   | `ComfyExtension`         |
| Adoption              | 90%+ of nodes           | Newer, less common       |
| Lazy inputs           | `lazy` option flag      | `lazy=True` parameter    |
| Dynamic outputs       | `IS_DYNAMIC` + methods  | Schema-based             |
