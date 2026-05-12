# Global Patching via `sys.modules` Scanning

## When to Use

- You need to monkey-patch a function that is imported **directly** by many modules (e.g., `from comfy.ldm.modules.attention import optimized_attention`).
- A targeted patch on one module isn't enough — other modules hold their own references to the original function.
- You're replacing a core utility (attention, sampling, encoding) and want **all** call sites to use your version.

## Problem

Patching the source module does not update references already imported elsewhere:

```python
import comfy.ldm.modules.attention as attn
attn.optimized_attention = my_version  # only patches the module attr

# But model.py did: from comfy.ldm.modules.attention import optimized_attention
# That local name still points to the ORIGINAL function.
```

## Solution: Scan `sys.modules` and Replace References

Walk every loaded module, find objects that hold a reference to the target function, and replace it.

```python
import sys
import types
import importlib
import logging

logger = logging.getLogger("MyNode")

# Track what we patched for debugging / undo
_patched_modules: dict[str, list[str]] = {}


def find_function(module_path: str, func_name: str):
    """Import a module and return the function object."""
    mod = importlib.import_module(module_path)
    func = getattr(mod, func_name, None)
    if func is None:
        raise AttributeError(f"{module_path} has no attribute {func_name}")
    return func


def global_patch(module_path: str, func_name: str, replacement):
    """
    Replace `func_name` in `module_path` AND in every module that
    imported it via `from module import func_name`.
    """
    original = find_function(module_path, func_name)
    patched = 0

    for mod_name, mod in list(sys.modules.items()):
        if mod is None:
            continue

        # Case 1: The module IS the source — patch its attribute directly
        if mod_name == module_path:
            setattr(mod, func_name, replacement)
            _patched_modules.setdefault(mod_name, []).append(func_name)
            patched += 1
            continue

        # Case 2: The module has the function as an attribute (from X import Y)
        if not hasattr(mod, func_name):
            continue

        current = getattr(mod, func_name)
        if current is original:
            setattr(mod, func_name, replacement)
            _patched_modules.setdefault(mod_name, []).append(func_name)
            patched += 1

    logger.info("Patched %s.%s in %d modules", module_path, func_name, patched)
    return patched


def patch_optimized_attention():
    """
    Replace optimized_attention with a version that supports
    custom attention processors (e.g., for IP-Adapter, attention masking).
    """
    import torch
    import comfy.model_management as model_management

    source_module = "comfy.ldm.modules.attention"
    func_name = "optimized_attention"

    # Store original for fallback
    original_func = find_function(source_module, func_name)

    def patched_optimized_attention(q, k, v, heads, mask=None, attn_precision=None, skip_reshape=False, skip_output_reshape=False):
        """Custom attention that injects hooks before the attention op."""
        # --- Pre-attention hook ---
        # Example: scale q/k by a custom factor
        hook = get_active_attention_hook()
        if hook is not None:
            q, k, v = hook.before_attention(q, k, v, heads)

        # --- Call original ---
        result = original_func(
            q, k, v, heads,
            mask=mask,
            attn_precision=attn_precision,
            skip_reshape=skip_reshape,
            skip_output_reshape=skip_output_reshape,
        )

        # --- Post-attention hook ---
        if hook is not None:
            result = hook.after_attention(result)

        return result

    count = global_patch(source_module, func_name, patched_optimized_attention)
    return count


# Simple hook registry
_active_hook = None

class AttentionHook:
    def before_attention(self, q, k, v, heads):
        return q, k, v

    def after_attention(self, result):
        return result

def get_active_attention_hook():
    return _active_hook

def set_attention_hook(hook):
    global _active_hook
    _active_hook = hook


def get_patched_modules() -> dict[str, list[str]]:
    """Return a copy of the patch tracking dict for logging/debugging."""
    return dict(_patched_modules)


def log_patch_report():
    """Log which modules were patched."""
    for mod_name, attrs in _patched_modules.items():
        logger.info("  %s: patched %s", mod_name, ", ".join(attrs))


# ---- Node that activates the patch ----

class AttentionPatchNode:
    """Toggle the global attention patch on/off."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "_for_testing"

    def execute(self, enabled):
        if enabled:
            count = patch_optimized_attention()
            log_patch_report()
            print(f"[MyNode] Patched optimized_attention in {count} modules")
        return ()


NODE_CLASS_MAPPINGS = {"AttentionPatchNode": AttentionPatchNode}
```

## How It Works

```
sys.modules
  │
  ├── comfy.ldm.modules.attention   ← setattr(module, 'optimized_attention', replacement)
  ├── comfy.ldm.modules.diffusion   ← from comfy.ldm... import optimized_attention  ← patched
  ├── comfy.sd                       ← from comfy.ldm... import optimized_attention  ← patched
  ├── nodes_model_sampling          ← (no reference, skipped)
  └── ... (hundreds of modules)
```

The function compares identity (`is`) — only replacing references that still point to the **original** function object. If another patch already replaced it, it's left alone.

## Key Considerations

1. **Import order matters** — Run your patch **after** all custom nodes have loaded. Use `__init__.py` top-level code or a `SERVER_READY` hook. If you patch too early, modules imported later will get the original.
2. **Identity check (`is`)** — We check `current is original` to avoid double-patching or overwriting another custom node's patch. This is safe because Python interns function references.
3. **Thread safety** — `setattr` on module objects is atomic in CPython, but the function itself must be thread-safe if multiple samplers run concurrently.
4. **Memory** — The original function is kept alive by `_patched_modules` and the closure. If you need to undo the patch, store the original in a dict keyed by `(module_path, func_name)`.
5. **Performance** — Scanning hundreds of modules is O(n) per attribute. Run it once at startup, not on every execution.
6. **Undo / Reload** — To undo, call `global_patch(module_path, func_name, original_func)`. For hot-reload during development, re-run the scan after `importlib.reload()`.
7. **Logging** — Always log what you patched. Debugging "why is attention broken?" is much easier when you can see which modules were touched.
8. **Scope** — This pattern works for any top-level function, class, or constant. It does **not** patch methods on instances — use subclassing or `functools.wraps` for that.
