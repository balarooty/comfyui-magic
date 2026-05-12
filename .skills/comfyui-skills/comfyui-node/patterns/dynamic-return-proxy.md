# DynamicReturnTypes Proxy Pattern

## When to Use

- Your node returns types that other custom nodes may extend (e.g., samplers, schedulers, model types).
- You need the return type list to reflect the **current** set of registered types at access time, not at import time.
- Other nodes register new types after your node loads, and you want your dropdown/combo to stay in sync.

## Problem

ComfyUI evaluates `RETURN_TYPES` at import time. If another node file registers a new sampler after yours loads, your node's dropdown is frozen to the stale snapshot.

```python
# BROKEN: captured once at import, never updates
class MyNode:
    RETURN_TYPES = (comfy.samplers.SAMPLER_NAMES,)
```

## Solution: `DynamicReturnTypes` Proxy

A proxy class that delegates `__getitem__`, `__iter__`, and `__len__` to the live source list on every access.

```python
import comfy.samplers

class DynamicReturnTypes:
    """Proxy that reads the source list at access time, not import time."""

    def __init__(self, get_source):
        self._get_source = get_source  # callable -> list

    def __getitem__(self, index):
        return self._get_source()[index]

    def __iter__(self):
        return iter(self._get_source())

    def __len__(self):
        return len(self._get_source())

    def __repr__(self):
        return repr(self._get_source())

    def index(self, value):
        return self._get_source().index(value)

    def __contains__(self, value):
        return value in self._get_source()


# Build the proxy — reads comfy.samplers.SAMPLER_NAMES every time
DYNAMIC_SAMPLERS = DynamicReturnTypes(lambda: list(comfy.samplers.SAMPLER_NAMES))


class DynamicSamplerNode:
    """Example node that always sees the full, up-to-date sampler list."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sampler_name": (DYNAMIC_SAMPLERS,),
                "model": ("MODEL",),
            }
        }

    RETURN_TYPES = ("SAMPLER",)
    FUNCTION = "execute"
    CATEGORY = "sampling"

    def execute(self, sampler_name, model):
        sampler = comfy.samplers.sampler_object(sampler_name)
        return (sampler,)
```

## How It Works

| Access | What happens |
|---|---|
| `DYNAMIC_SAMPLERS[0]` | Calls `list(comfy.samplers.SAMPLER_NAMES)[0]` |
| `for s in DYNAMIC_SAMPLERS` | Iterates the live list |
| `len(DYNAMIC_SAMPLERS)` | Returns current count |

ComfyUI calls `INPUT_TYPES` and evaluates `RETURN_TYPES` each time the frontend requests the graph schema, so the proxy is re-evaluated naturally.

## Key Considerations

1. **Thread safety** — `comfy.samplers.SAMPLER_NAMES` is mutated during registration. In CPython the GIL makes list reads atomic, but if you mutate the proxy's internal cache you need a lock.
2. **Don't cache inside the proxy** — The whole point is fresh reads. Never store `self._cache = self._get_source()`.
3. **Works for any combo list** — Replace `SAMPLER_NAMES` with `SCHEDULER_NAMES`, custom enum lists, or any dynamically populated collection.
4. **Frontend sync** — ComfyUI's frontend polls `object_info` on page load and when the queue runs. The proxy ensures the backend always returns the latest list.
5. **Fallback values** — If your node stores a previously selected value that gets removed from the source list, the frontend will show a warning. Handle this in `execute()` with a default fallback.
