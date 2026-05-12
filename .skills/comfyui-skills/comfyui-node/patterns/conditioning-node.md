# Conditioning Node Pattern

## When to Use

Use this pattern for nodes that manipulate conditioning data — the text prompts and their encoded representations that guide the diffusion model. Conditioning in ComfyUI is a list of tuples containing tensors and metadata. This pattern covers combining, mixing, and modifying conditioning for multi-prompt workflows.

**Typical use cases:**
- Combining multiple text prompts
- Mixing prompt strengths (weighted blending)
- Setting area conditioning for inpainting
- Concatenating conditioning from different CLIP encoders
- Applying conditioning scheduling across timesteps

## Architecture

```
CONDITIONING A + CONDITIONING B → merge/mix → combined CONDITIONING
                                                    ↓
                                            list of (tensor, dict) tuples
                                            strength weighting
                                            area masking
```

## Key Concepts

| Concept | Detail |
|---|---|
| CONDITIONING type | `list[tuple[Tensor, dict]]` — each entry is `(cond_tensor, metadata)` |
| cond_tensor | Shape varies by model, typically `[B, seq_len, hidden_dim]` |
| metadata dict | Contains `cross_attn`, `pooled_output`, `area`, `strength`, `timestep_percent` |
| Combining | Appending multiple entries to the list (model sees all prompts) |
| Mixing | Weighted interpolation of conditioning tensors |

## Complete Code Example

```python
import torch

class ConditioningCombine:
    """Combines multiple conditioning inputs into a single conditioning list."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning_a": ("CONDITIONING",),
                "conditioning_b": ("CONDITIONING",),
            },
            "optional": {
                "conditioning_c": ("CONDITIONING",),
                "conditioning_d": ("CONDITIONING",),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("conditioning",)
    FUNCTION = "combine"
    CATEGORY = "conditioning"

    def combine(self, conditioning_a, conditioning_b, conditioning_c=None, conditioning_d=None):
        # CONDITIONING is a list of (tensor, dict) tuples
        combined = list(conditioning_a) + list(conditioning_b)

        if conditioning_c is not None:
            combined += list(conditioning_c)
        if conditioning_d is not None:
            combined += list(conditioning_d)

        return (combined,)
```

## CONDITIONING Data Structure

```python
# A CONDITIONING value looks like this:
conditioning = [
    (cond_tensor, {
        "cross_attn": cond_tensor,      # Cross-attention conditioning
        "pooled_output": pooled_tensor,  # Pooled text embedding (for SDXL)
        "area": (x, y, w, h),           # Optional: area conditioning
        "strength": 1.0,                 # Conditioning strength
        "set_area_to_bounds": False,
        "timestep_percent_range": (0.0, 1.0),  # When this conditioning is active
    }),
]

# Multiple entries = multiple prompts are all passed to the model
# The model processes them and applies them based on area/strength/timestep
```

## Key Considerations

1. **CONDITIONING is a list of tuples.** Always use `list()` to convert before concatenating. Don't try to merge tensors directly.

2. **Metadata dict is per-entry.** Each conditioning entry has its own dict with `cross_attn`, `pooled_output`, `area`, `strength`, etc.

3. **Area conditioning.** Setting `"area"` in the metadata restricts that conditioning to a spatial region. Useful for multi-prompt workflows (e.g., "dog" on left, "cat" on right).

4. **Strength range.** Strength can be any float. Values > 1 amplify the prompt's influence; values < 1 reduce it.

5. **Pooled output for SDXL.** SDXL models use `pooled_output` in addition to cross-attention. Ensure both are set when combining SDXL conditioning.

6. **Timestep ranges.** `"timestep_percent_range": (0.0, 0.5)` means the conditioning only applies during the first 50% of denoising steps.

7. **Empty conditioning.** Create empty conditioning with `[]` — but most workflows always have at least one entry.

## Variations

### Strength Mixer

```python
class ConditioningStrengthMix:
    """Mixes two conditioning inputs with adjustable weights."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning_a": ("CONDITIONING",),
                "conditioning_b": ("CONDITIONING",),
                "mix_ratio": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "0.0 = all A, 1.0 = all B"
                }),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "mix"
    CATEGORY = "conditioning"

    def mix(self, conditioning_a, conditioning_b, mix_ratio):
        result = []

        for cond_a_tensor, meta_a in conditioning_a:
            for cond_b_tensor, meta_b in conditioning_b:
                # Interpolate conditioning tensors
                mixed_tensor = cond_a_tensor * (1 - mix_ratio) + cond_b_tensor * mix_ratio

                # Merge metadata, preferring A's metadata
                mixed_meta = dict(meta_a)
                mixed_meta["cross_attn"] = mixed_tensor

                # Mix pooled outputs if both have them
                if "pooled_output" in meta_a and "pooled_output" in meta_b:
                    pooled_a = meta_a["pooled_output"]
                    pooled_b = meta_b["pooled_output"]
                    mixed_meta["pooled_output"] = pooled_a * (1 - mix_ratio) + pooled_b * mix_ratio

                result.append((mixed_tensor, mixed_meta))

        return (result,)
```

### Area Conditioning

```python
class ConditioningSetArea:
    """Restricts conditioning to a specific area of the image."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("CONDITIONING",),
                "width": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8}),
                "height": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8}),
                "x": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "y": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
            },
            "optional": {
                "set_area_to_bounds": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "set_area"
    CATEGORY = "conditioning"

    def set_area(self, conditioning, width, height, x, y, strength, set_area_to_bounds=False):
        result = []
        for cond_tensor, meta in conditioning:
            new_meta = dict(meta)
            new_meta["area"] = (x, y, width, height)
            new_meta["strength"] = strength
            new_meta["set_area_to_bounds"] = set_area_to_bounds
            result.append((cond_tensor, new_meta))
        return (result,)
```

### Timestep Conditioning

```python
class ConditioningTimestep:
    """Sets the timestep range for when conditioning is active."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("CONDITIONING",),
                "start_percent": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "end_percent": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "set_timestep"
    CATEGORY = "conditioning"

    def set_timestep(self, conditioning, start_percent, end_percent):
        result = []
        for cond_tensor, meta in conditioning:
            new_meta = dict(meta)
            new_meta["timestep_percent_range"] = (start_percent, end_percent)
            result.append((cond_tensor, new_meta))
        return (result,)
```

### Conditioning Concat (Cross-Attention Concatenation)

```python
class ConditioningConcat:
    """Concatenates conditioning tensors along the sequence dimension."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning_a": ("CONDITIONING",),
                "conditioning_b": ("CONDITIONING",),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "concat"
    CATEGORY = "conditioning"

    def concat(self, conditioning_a, conditioning_b):
        result = []

        # Take first entry from each (most common case)
        cond_a, meta_a = conditioning_a[0]
        cond_b, meta_b = conditioning_b[0]

        # Concatenate along sequence dimension
        # cond shape: [B, seq_len, hidden_dim]
        concat_cond = torch.cat([cond_a, cond_b], dim=1)

        # Merge metadata
        meta = dict(meta_a)
        meta["cross_attn"] = concat_cond

        # Concatenate pooled outputs if present
        if "pooled_output" in meta_a and "pooled_output" in meta_b:
            meta["pooled_output"] = torch.cat([
                meta_a["pooled_output"],
                meta_b["pooled_output"]
            ], dim=-1)

        result.append((concat_cond, meta))
        return (result,)
```

### ConditioningZero (Empty/Zeroed Conditioning)

```python
class ConditioningZero:
    """Creates zero conditioning that has no effect on generation."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("CONDITIONING",),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "zero"
    CATEGORY = "conditioning"

    def zero(self, conditioning):
        result = []
        for cond_tensor, meta in conditioning:
            # Zero out the conditioning tensor
            zero_tensor = torch.zeros_like(cond_tensor)
            new_meta = dict(meta)
            new_meta["cross_attn"] = zero_tensor
            if "pooled_output" in new_meta:
                new_meta["pooled_output"] = torch.zeros_like(new_meta["pooled_output"])
            result.append((zero_tensor, new_meta))
        return (result,)
```
