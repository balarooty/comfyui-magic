# Model Patcher Node Pattern

## When to Use

Use this pattern when you need to modify a model's behavior without replacing it entirely — applying LoRAs, adjusting attention mechanisms, modifying scheduler parameters, or injecting hooks. The model patcher pattern clones the model reference and applies modifications to `model_options` or `transformer_options`, leaving the original model untouched.

## Anatomy

```
model.clone()            → creates a shallow copy with independent options
model_options            → dictionary of model-level configuration
transformer_options      → dictionary controlling attention, hooks, patches
model.set_model_patch()  → injects custom patches into the model
```

## Complete Code Example: LoRA Strength Adjuster

```python
import torch

class LoRAStrengthAdjuster:
    """Adjusts the strength of an already-loaded LoRA on a model."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "strength_model": ("FLOAT", {
                    "default": 1.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.01,
                    "tooltip": "Strength of the LoRA applied to the model (UNet)."
                }),
                "strength_clip": ("FLOAT", {
                    "default": 1.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.01,
                    "tooltip": "Strength of the LoRA applied to CLIP."
                }),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    FUNCTION = "adjust_strength"
    CATEGORY = "model/patchers"

    def adjust_strength(self, model, strength_model, strength_clip):
        # Clone the model to avoid mutating the original
        model_patched = model.clone()

        # Modify model_options to scale LoRA contributions
        # The "lora_patch" key is read by ComfyUI's model patching system
        if "lora_patch" in model_patched.model_options:
            lora_patch = model_patched.model_options["lora_patch"]
            for key in lora_patch:
                if isinstance(lora_patch[key], torch.Tensor):
                    lora_patch[key] = lora_patch[key] * strength_model

        return (model_patched,)

NODE_CLASS_MAPPINGS = {
    "LoRAStrengthAdjuster": LoRAStrengthAdjuster,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoRAStrengthAdjuster": "LoRA Strength Adjuster",
}
```

## Key Considerations

### model.clone() Is Shallow
- `model.clone()` creates a new reference to the same underlying model weights.
- `model_options` and `transformer_options` are copied independently, so changes to the clone do not affect the original.
- This is cheap — no tensor duplication occurs until a patch modifies specific weight tensors.

### model_options vs transformer_options

| Option Type | Purpose | Example Keys |
|---|---|---|
| `model_options` | High-level model behavior | `lora_patch`, `sampler_cfg_function`, `negative_prompt` |
| `transformer_options` | Per-layer attention/hooks | `patches`, `hooks`, `cond_or_uncond` |

### Patching Specific Layers
- Use `model.set_model_patch(tensor, key)` to inject a patch tensor for a specific key.
- Use `model.set_model_attn1_patch(patch_fn)` for custom self-attention patches.
- Use `model.set_model_attn2_patch(patch_fn)` for custom cross-attention patches.

### Return the Clone
- Always return the cloned model, never the original. Downstream nodes expect an unmodified original.
- If your node has multiple outputs, return the clone for each relevant output.

## Variations

### Attention Override Patch

```python
def patch_attention(self, model, scale):
    model_patched = model.clone()

    def attn_patch(q, k, v, extra_options):
        # Scale attention scores
        return q, k * scale, v

    model_patched.set_model_attn2_patch(attn_patch)
    return (model_patched,)
```

### Transformer Options Injection

```python
def inject_options(self, model, guidance_scale):
    model_patched = model.clone()

    # Modify transformer-level options
    model_patched.model_options["sampler_cfg_function"] = lambda args: guidance_scale

    return (model_patched,)
```

### Weight Patching (Modifying Actual Weights)

```python
def apply_weight_patch(self, model, key, value, strength):
    model_patched = model.clone()

    # Get the current weight tensor
    weight = model_patched.model.get_parameter(key)

    # Apply the modification
    new_weight = weight + (value - weight) * strength

    # Set the patched weight
    model_patched.model.set_parameter(key, new_weight)

    return (model_patched,)
```

### Combining Multiple Patches

```python
def combine_patches(self, model_a, model_b, ratio):
    # Clone model_a as the base
    combined = model_a.clone()

    # Merge patches from model_b with the given ratio
    if "lora_patch" in model_b.model_options:
        for key, tensor in model_b.model_options["lora_patch"].items():
            if key in combined.model_options.get("lora_patch", {}):
                combined.model_options["lora_patch"][key] = (
                    combined.model_options["lora_patch"][key] * (1.0 - ratio)
                    + tensor * ratio
                )

    return (combined,)
```
