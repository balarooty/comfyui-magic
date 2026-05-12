# Model Loader Node Pattern

## When to Use

Use this pattern when your node loads a file from disk — checkpoints, LoRAs, ControlNet models, VAEs, or any other asset stored in ComfyUI's configured model directories. This pattern handles file discovery, caching, and change detection.

## Anatomy

```
folder_paths            → resolves model directory paths
IS_CHANGED (classmethod)→ triggers re-execution when the file changes
annotated_filepath       → attaches metadata to the filepath for caching
RETURN_TYPES            → typically MODEL, CLIP, VAE or similar
```

## Complete Code Example: Checkpoint Loader

```python
import hashlib
import os
import folder_paths
from comfy.utils import load_torch_file

class CheckpointLoaderSimple:
    """Loads a Stable Diffusion checkpoint and returns its components."""

    @classmethod
    def INPUT_TYPES(cls):
        # Populate the dropdown from the checkpoints directory
        checkpoint_files = folder_paths.get_filename_list("checkpoints")
        return {
            "required": {
                "ckpt_name": (checkpoint_files, {
                    "tooltip": "The name of the checkpoint file to load."
                }),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("model", "clip", "vae")
    FUNCTION = "load_checkpoint"
    CATEGORY = "loaders"

    @classmethod
    def IS_CHANGED(cls, ckpt_name):
        # Resolve the full path to the checkpoint file
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)

        # Compute a hash of the file to detect changes.
        # This ensures the node re-executes when the file is updated.
        m = hashlib.sha256()
        with open(ckpt_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                m.update(chunk)

        # Annotate the hash with the filepath for ComfyUI's caching system
        return m.hexdigest()

    def load_checkpoint(self, ckpt_name):
        # Resolve full path from the model directory alias
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)

        # Load the checkpoint tensors
        checkpoint = load_torch_file(ckpt_path)

        # Use ComfyUI's built-in model extraction utilities
        from comfy.sd import load_model_weights, VAE, CLIP

        # Extract components from the checkpoint
        model = load_model_weights(checkpoint, "")
        clip = CLIP(checkpoint)
        vae = VAE(checkpoint)

        return (model, clip, vae)

NODE_CLASS_MAPPINGS = {
    "CheckpointLoaderSimple": CheckpointLoaderSimple,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CheckpointLoaderSimple": "Load Checkpoint",
}
```

## Key Considerations

### folder_paths System
- `folder_paths.get_filename_list("checkpoints")` returns a list of relative filenames from all registered directories of that type.
- `folder_paths.get_full_path("checkpoints", ckpt_name)` resolves the relative name to an absolute path.
- Common directory aliases: `"checkpoints"`, `"loras"`, `"vae"`, `"controlnet"`, `"clip"`, `"embeddings"`, `"upscale_models"`.

### IS_CHANGED for Caching
- ComfyUI caches node outputs. If `IS_CHANGED` returns the same value as last time, the node is skipped.
- For file-based nodes, hash the file contents so the node re-executes when the file changes.
- Return `float("inf")` to always re-execute (use sparingly).
- Return `True` to always re-execute (less common convention).

### Annotated Filepath
- When `IS_CHANGED` returns a value, ComfyUI associates it with the node's inputs for caching.
- The file hash acts as a cache key — if the file changes, the hash changes, and downstream nodes re-execute.

### Performance
- Model loading is expensive. Consider using `@functools.lru_cache` or ComfyUI's internal caching.
- `load_torch_file` supports `safetensors` and `ckpt` formats.
- Use `safetensors` when possible for safer and faster loading.

## Variations

### LoRA Loader

```python
@classmethod
def INPUT_TYPES(cls):
    lora_files = folder_paths.get_filename_list("loras")
    return {
        "required": {
            "lora_name": (lora_files, ),
            "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
            "strength_clip": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
        },
    }

RETURN_TYPES = ("MODEL", "CLIP")
FUNCTION = "load_lora"
CATEGORY = "loaders"

@classmethod
def IS_CHANGED(cls, lora_name, strength_model, strength_clip):
    lora_path = folder_paths.get_full_path("loras", lora_name)
    m = hashlib.sha256()
    with open(lora_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            m.update(chunk)
    return m.hexdigest()
```

### VAE Loader

```python
@classmethod
def INPUT_TYPES(cls):
    vae_files = folder_paths.get_filename_list("vae")
    return {
        "required": {
            "vae_name": (vae_files, ),
        },
    }

RETURN_TYPES = ("VAE",)
FUNCTION = "load_vae"
CATEGORY = "loaders"

def load_vae(self, vae_name):
    vae_path = folder_paths.get_full_path("vae", vae_name)
    vae_sd = load_torch_file(vae_path)
    from comfy.sd import VAE
    vae = VAE(sd=vae_sd)
    return (vae,)
```

### Multi-Directory Search

```python
@classmethod
def INPUT_TYPES(cls):
    # Search across multiple directory types
    models = []
    for model_dir in ["checkpoints", "diffusion_models"]:
        models.extend(folder_paths.get_filename_list(model_dir))
    return {
        "required": {
            "model_name": (models, ),
        },
    }
```
