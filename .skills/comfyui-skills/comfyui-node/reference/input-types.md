# Input Types Reference

Complete reference for all ComfyUI input types and their options.

## Primitive Types

### INT

Integer input with optional slider.

```python
("INT", {
    "default": 512,
    "min": 1,
    "max": 8192,
    "step": 1,
    "tooltip": "Width in pixels",
})
```

### FLOAT

Floating-point input with optional slider.

```python
("FLOAT", {
    "default": 0.75,
    "min": 0.0,
    "max": 1.0,
    "step": 0.01,
    "tooltip": "Strength value",
})
```

### STRING

Text input, optionally multiline.

```python
("STRING", {
    "default": "",
    "multiline": True,
    "placeholder": "Enter your prompt here...",
    "dynamicPrompts": True,
    "tooltip": "Text prompt",
})
```

### BOOLEAN

Toggle/checkbox input.

```python
("BOOLEAN", {
    "default": True,
    "label_on": "enabled",
    "label_off": "disabled",
    "tooltip": "Enable feature",
})
```

## COMBO (Dropdown)

Dropdown selection from a fixed list or folder_paths.

```python
# Static list
(["option1", "option2", "option3"],)

# With default (first item is default)
(["fast", "quality", "balanced"],)

# From folder_paths (auto-populates with files in a directory)
("folder_paths:checkpoints",)
("folder_paths:loras",)
("folder_paths:vae",)
("folder_paths:embeddings",)
("folder_paths:controlnet",)
("folder_paths:upscale_models",)
```

## Tensor Types

Data tensors that flow between nodes.

### IMAGE

Image tensor of shape `[B, H, W, C]` where C is typically 3 (RGB) or 4 (RGBA).

```python
("IMAGE",)
```

### LATENT

Latent space tensor from VAE encoding. Shape `[B, C, H, W]` where C is typically 4.

```python
("LATENT",)
```

### MASK

Mask tensor of shape `[B, H, W]`. Values typically 0.0 (hidden) to 1.0 (visible).

```python
("MASK",)
```

### AUDIO

Audio waveform tensor.

```python
("AUDIO",)
```

## Model Types

ComfyUI model objects passed between nodes.

### MODEL

The main diffusion model object (UNet, DiT, etc.).

```python
("MODEL",)
```

### CLIP

CLIP text encoder model.

```python
("CLIP",)
```

### VAE

Variational Autoencoder model.

```python
("VAE",)
```

### CONDITIONING

Conditioning data (text embeddings + other conditioning).

```python
("CONDITIONING",)
```

## Sampling Types

Objects used in the sampling pipeline.

### NOISE

Noise generator interface.

```python
("NOISE",)
```

### SAMPLER

Sampler algorithm (euler, dpm, etc.).

```python
("SAMPLER",)
```

### SIGMAS

Sigma schedule values for the sampler.

```python
("SIGMAS",)
```

### GUIDER

Guidance strategy (CFG, uncond, etc.).

```python
("GUIDER",)
```

## Custom Types

Any uppercase string can be a custom type. The type must match between connected nodes.

```python
# Define custom type
RETURN_TYPES = ("MY_CUSTOM_TYPE",)

# Another node accepts it
("MY_CUSTOM_TYPE",)
```

## Wildcard Type

Accept any type of input.

```python
("*",)
```

## Input Options

All input types accept these options in the dict:

| Option          | Types         | Description                                      |
|-----------------|---------------|--------------------------------------------------|
| `default`       | All           | Default value when unconnected                   |
| `min`           | INT, FLOAT    | Minimum allowed value                            |
| `max`           | INT, FLOAT    | Maximum allowed value                            |
| `step`          | INT, FLOAT    | Slider step increment                            |
| `label_on`      | BOOLEAN       | Text shown when enabled                          |
| `label_off`     | BOOLEAN       | Text shown when disabled                         |
| `defaultInput`  | All           | Default input value (for unconnected ports)      |
| `forceInput`    | All           | Force as input port (never show widget)          |
| `multiline`     | STRING        | Enable multi-line text area                      |
| `placeholder`   | STRING        | Placeholder text when empty                      |
| `dynamicPrompts`| STRING        | Enable dynamic prompt syntax                     |
| `lazy`          | All           | Defer evaluation until value is accessed         |
| `rawLink`       | All           | Pass raw link data instead of resolved value     |
| `tooltip`       | All           | Hover tooltip text                               |

### default

Value used when the input port is not connected.

```python
("INT", {"default": 512})
("FLOAT", {"default": 0.75})
("STRING", {"default": "hello"})
("BOOLEAN", {"default": False})
```

### min / max / step

Constrain numeric inputs.

```python
("INT", {"default": 20, "min": 1, "max": 100, "step": 1})
("FLOAT", {"default": 7.5, "min": 1.0, "max": 20.0, "step": 0.1})
```

### forceInput

Always show as an input port, never as a widget. Useful for types that shouldn't have inline editing.

```python
("IMAGE", {"forceInput": True})
("STRING", {"forceInput": True, "default": ""})
```

### multiline

Enable multi-line text area for STRING inputs.

```python
("STRING", {
    "default": "",
    "multiline": True,
    "placeholder": "Enter prompt...",
})
```

### placeholder

Placeholder text shown in empty text fields.

```python
("STRING", {"default": "", "placeholder": "Describe the image..."})
```

### dynamicPrompts

Enable dynamic prompt syntax (e.g., `{option1|option2}`).

```python
("STRING", {"default": "", "multiline": True, "dynamicPrompts": True})
```

### lazy

Defer evaluation until the value is actually used. Useful for expensive computations.

```python
("IMAGE", {"lazy": True})
("LATENT", {"lazy": True})
```

### rawLink

When connected, pass the raw link data instead of the resolved value. Advanced pattern for custom data passing.

```python
("STRING", {"rawLink": True})
```

### tooltip

Hover tooltip text shown in the UI.

```python
("FLOAT", {"default": 0.5, "tooltip": "Blend strength between 0 and 1"})
```

## Hidden Inputs

System-injected inputs. Not shown in the UI but available in execute().

```python
"hidden": {
    "unique_id": "UNIQUE_ID",
    "prompt": "PROMPT",
    "extra_pnginfo": "EXTRA_PNGINFO",
    "dynprompt": "DYNPROMPT",
}
```

### UNIQUE_ID

String identifier for the current node instance. Unique within a workflow.

```python
"hidden": {"unique_id": "UNIQUE_ID"}

def execute(self, unique_id, **kwargs):
    print(f"Executing node {unique_id}")
```

### PROMPT

Full workflow prompt dict. Contains all node definitions and connections.

```python
"hidden": {"prompt": "PROMPT"}

def execute(self, prompt, **kwargs):
    # Access other node definitions
    for node_id, node_data in prompt.items():
        print(f"Node {node_id}: {node_data['class_type']}")
```

### EXTRA_PNGINFO

Metadata dict passed through for PNG saving. Contains workflow info.

```python
"hidden": {"extra_pnginfo": "EXTRA_PNGINFO"}

def execute(self, extra_pnginfo, **kwargs):
    # Attach workflow metadata to saved images
    metadata = extra_pnginfo.get("workflow", {})
```

### DYNPROMPT

Dynamic prompt data for prompt manipulation.

```python
"hidden": {"dynprompt": "DYNPROMPT"}
```

## folder_paths Integration

Use folder_paths to populate COMBO dropdowns with files from standard directories.

```python
import folder_paths

@classmethod
def INPUT_TYPES(s):
    return {
        "required": {
            # Standard checkpoint directory
            "model_name": (folder_paths.get_filename_list("checkpoints"),),

            # Other standard directories
            "lora_name": (folder_paths.get_filename_list("loras"),),
            "vae_name": (folder_paths.get_filename_list("vae"),),
            "embedding_name": (folder_paths.get_filename_list("embeddings"),),
            "controlnet_name": (folder_paths.get_filename_list("controlnet"),),
            "upscale_model_name": (folder_paths.get_filename_list("upscale_models"),),
        },
    }
```

### Custom folder_paths

Register custom directories for COMBO inputs.

```python
import folder_paths

# Register a custom models directory
folder_paths.add_model_folder_path("my_custom_models", "/path/to/models")

@classmethod
def INPUT_TYPES(s):
    return {
        "required": {
            "custom_model": (folder_paths.get_filename_list("my_custom_models"),),
        },
    }
```

### folder_paths with extensions filter

Filter files by extension.

```python
import folder_paths
import os

@classmethod
def INPUT_TYPES(s):
    # Get only .safetensors files
    models = [
        m for m in folder_paths.get_filename_list("checkpoints")
        if m.endswith(".safetensors")
    ]
    return {
        "required": {
            "model_name": (models,),
        },
    }
```
