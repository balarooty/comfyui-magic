# Lazy Evaluation with `check_lazy_status`

## When to Use

- Your node has expensive inputs (e.g., model loading, VAE decode) that are only needed in certain code paths.
- You want to conditionally skip inputs based on earlier input values.
- You want to short-circuit evaluation — if a control flag is False, don't evaluate the downstream branch.
- You want to defer prompt encoding until you know it's actually needed.

## Problem

By default, ComfyUI evaluates **all** of a node's inputs before calling `execute()`. Even if your node only uses `model_a` when `use_model_b` is False, both models are loaded and passed in.

```python
class MergeModels:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_a": ("MODEL",),
                "model_b": ("MODEL",),  # always loaded, even if unused
                "use_b": ("BOOLEAN", {"default": False}),
            }
        }

    def execute(self, model_a, model_b, use_b):
        if use_b:
            return (model_b,)
        return (model_a,)  # model_b was loaded for nothing
```

## Solution: `check_lazy_status` + `lazy` Input Declaration

Mark inputs as `"lazy": True` and implement `check_lazy_status()` as a classmethod. ComfyUI calls it repeatedly, asking which input to evaluate next.

```python
import torch


class MergeModels:
    """Merge two models with configurable ratio. Only loads model_b if needed."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_a": ("MODEL",),
                "model_b": ("MODEL", {"lazy": True}),
                "use_b": ("BOOLEAN", {"default": False}),
                "blend_ratio": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "execute"
    CATEGORY = "model/merge"

    @classmethod
    def check_lazy_status(cls, use_b, **kwargs):
        """
        Called by the executor to determine which input to request next.

        Returns:
            - str: name of the input to evaluate next
            - None: all needed inputs are available, proceed to execute()

        The executor calls this repeatedly:
            1. First call: only non-lazy inputs are available (model_a, use_b, blend_ratio)
            2. Returns "model_b" → executor evaluates and provides model_b
            3. Second call: model_a, model_b, use_b, blend_ratio all available
            4. Returns None → executor calls execute()
        """
        if use_b and "model_b" not in kwargs:
            return "model_b"
        return None  # ready to execute

    def execute(self, model_a, model_b=None, use_b=False, blend_ratio=0.5):
        if not use_b or model_b is None:
            return (model_a,)

        # Simple linear interpolation of model weights
        merged = model_a.clone()
        for key in merged.model.state_dict():
            if key in model_b.model.state_dict():
                w_a = merged.model.state_dict()[key]
                w_b = model_b.model.state_dict()[key]
                merged.model.state_dict()[key].copy_(
                    w_a * (1 - blend_ratio) + w_b * blend_ratio
                )
        return (merged,)


class ConditionalVAEDecode:
    """Decode latent only if quality check passes. Otherwise return a placeholder."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "samples": ("LATENT",),
                "vae": ("VAE", {"lazy": True}),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
                "quality_score": ("FLOAT", {"default": 0.8}),
            }
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN")
    RETURN_NAMES = ("image", "passed_check")
    FUNCTION = "execute"
    CATEGORY = "latent"

    @classmethod
    def check_lazy_status(cls, samples, threshold, quality_score, **kwargs):
        # Only request VAE decode if quality is sufficient
        if quality_score >= threshold and "vae" not in kwargs:
            return "vae"
        return None

    def execute(self, samples, vae=None, threshold=0.5, quality_score=0.8):
        if quality_score < threshold or vae is None:
            # Return a black 64x64 image as placeholder
            placeholder = torch.zeros(1, 64, 64, 3)
            return (placeholder, False)

        decoded = vae.decode(samples["samples"])
        return (decoded, True)


class SmartPromptRouter:
    """
    Route prompt to one of two CLIP encoders based on a selector.
    Only loads the selected encoder.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "clip_a": ("CLIP", {"lazy": True}),
                "clip_b": ("CLIP", {"lazy": True}),
                "use_clip_b": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "execute"
    CATEGORY = "conditioning"

    @classmethod
    def check_lazy_status(cls, text, use_clip_b, **kwargs):
        # Only request the CLIP we actually need
        if use_clip_b:
            if "clip_b" not in kwargs:
                return "clip_b"
        else:
            if "clip_a" not in kwargs:
                return "clip_a"
        return None

    def execute(self, text, clip_a=None, clip_b=None, use_clip_b=False):
        clip = clip_b if use_clip_b else clip_a
        if clip is None:
            raise RuntimeError("Required CLIP encoder was not provided")
        tokens = clip.tokenize(text)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return ([[cond, {"pooled_output": pooled}]],)


NODE_CLASS_MAPPINGS = {
    "MergeModels": MergeModels,
    "ConditionalVAEDecode": ConditionalVAEDecode,
    "SmartPromptRouter": SmartPromptRouter,
}
```

## How the Executor Calls `check_lazy_status`

```
User clicks Queue
        │
        ▼
Executor: MergeModels needs inputs
  ├── model_a        → always loaded (not lazy)
  ├── use_b          → always loaded (not lazy)  → value: True
  ├── blend_ratio    → always loaded (not lazy)  → value: 0.5
  └── model_b        → LAZY, not yet requested
        │
        ▼
Executor calls: check_lazy_status(use_b=True, model_a=..., blend_ratio=0.5)
  └── Returns "model_b"  → executor loads model_b from upstream node
        │
        ▼
Executor calls: check_lazy_status(use_b=True, model_a=..., model_b=..., blend_ratio=0.5)
  └── Returns None  → all inputs ready
        │
        ▼
Executor calls: execute(model_a=..., model_b=..., use_b=True, blend_ratio=0.5)
  └── Returns merged model
```

## Key Considerations

1. **Declare `"lazy": True`** — Only inputs marked lazy participate in deferred evaluation. Non-lazy inputs are always evaluated before `check_lazy_status` is called.
2. **`check_lazy_status` is a classmethod** — It receives the **current known values** as keyword arguments. Lazy inputs that haven't been requested yet are **not** in `kwargs`.
3. **Return value** — Return the **name** (string) of the next input to evaluate, or `None` when ready to execute. Don't return a list.
4. **Multiple lazy inputs** — The executor calls `check_lazy_status` once per lazy input. If you have 3 lazy inputs and conditionally need 2, it will be called up to 3 times.
5. **Default values in execute()** — Always give lazy parameters a default value (`None`) in `execute()`, because they may never be requested.
6. **No side effects in check_lazy_status** — This method may be called multiple times with different partial inputs. Don't modify state.
7. **Breaking cycles** — Lazy evaluation can break circular dependencies in complex graphs. If node A and B both need each other's output conditionally, lazy evaluation lets one side defer.
8. **VRAM savings** — The primary benefit. Deferring a model load until it's needed can save gigabytes of VRAM in conditional workflows.
9. **Frontend unaware** — The node UI still shows all inputs. The lazy deferral happens server-side during execution only.
