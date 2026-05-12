# Iterator Pattern

## When to Use

- Automated sweeps over parameter combinations (sampler × scheduler × steps × CFG)
- Queue-driven batch processing where each execution advances to the next combination
- Nodes that must re-execute on every queue run even when inputs haven't changed
- Generating grids, comparison charts, or systematic explorations

## Pattern

Use a class-level counter that increments per execution. `IS_CHANGED` returns `random.random()` to force re-execution. Auto-stop when combinations are exhausted by raising an exception.

```python
import random
import itertools
import torch
import numpy as np

import comfy.samplers
import folder_paths


class SamplerSchedulerIterator:
    """Iterates through all sampler × scheduler combinations automatically."""

    # Class-level state — shared across instances, persists across queue runs
    _counter = 0
    _combinations = []
    _last_params_hash = None

    @classmethod
    def INPUT_TYPES(cls):
        samplers = comfy.samplers.KSampler.SAMPLERS
        schedulers = comfy.samplers.KSampler.SCHEDULERS

        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent": ("LATENT",),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "reset": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("LATENT", "STRING")
    RETURN_NAMES = ("samples", "info")
    FUNCTION = "sample"
    CATEGORY = "sampling"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Always return a new value to force re-execution on every queue run."""
        return random.random()

    @classmethod
    def _ensure_combinations(cls, samplers, schedulers):
        """Build combinations list if samplers/schedulers changed."""
        current_hash = hash((tuple(samplers), tuple(schedulers)))
        if cls._last_params_hash != current_hash:
            cls._combinations = list(itertools.product(samplers, schedulers))
            cls._counter = 0
            cls._last_params_hash = current_hash

    def sample(self, model, positive, negative, latent,
               steps=20, cfg=7.0, seed=0, reset=False):

        samplers = comfy.samplers.KSampler.SAMPLERS
        schedulers = comfy.samplers.KSampler.SCHEDULERS
        self._ensure_combinations(samplers, schedulers)

        if reset:
            self.__class__._counter = 0
            return (latent, "Counter reset to 0")

        # Check if exhausted
        if self._counter >= len(self._combinations):
            self.__class__._counter = 0
            raise StopIteration(
                f"All {len(self._combinations)} combinations exhausted. "
                f"Queue will stop. Re-enable to restart."
            )

        # Get current combination
        sampler_name, scheduler_name = self._combinations[self._counter]
        current_index = self._counter

        # Advance counter for next execution
        self.__class__._counter += 1

        # Run the sampler
        from comfy.sd import decode_latent_batch
        from nodes import KSampler

        sampler_node = KSampler()
        (output_latent,) = sampler_node.sample(
            model=model,
            seed=seed,
            steps=steps,
            cfg=cfg,
            sampler_name=sampler_name,
            scheduler=scheduler_name,
            positive=positive,
            negative=negative,
            latent_image=latent,
            denoise=1.0,
        )

        info = (
            f"[{current_index + 1}/{len(self._combinations)}] "
            f"sampler={sampler_name}, scheduler={scheduler_name}, "
            f"steps={steps}, cfg={cfg}, seed={seed}"
        )

        return (output_latent, info)


NODE_CLASS_MAPPINGS = {
    "SamplerSchedulerIterator": SamplerSchedulerIterator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SamplerSchedulerIterator": "Sampler Scheduler Iterator",
}
```

## Integration with Queue Events

To auto-stop the ComfyUI queue when iterations are exhausted, listen for `execution_success` on the frontend. In a companion JavaScript file (`web/js/iterator.js`):

```javascript
import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

api.addEventListener("execution_success", () => {
    // Check if any iterator node reported exhaustion
    // If so, clear the queue
    const queueRemaining = app.ui.queueRemaining;
    if (queueRemaining <= 0) {
        // Queue naturally drained — nothing extra to do
    }
});
```

## Key Considerations

- **`IS_CHANGED` returning `random.random()`** is the core trick. It tells ComfyUI the node's output changed every time, forcing re-execution even with identical inputs. Without this, the node only runs once.
- **Class-level state** (`_counter`) persists across queue runs within the same server session. Instance-level state would reset each execution due to how ComfyUI instantiates nodes.
- **StopIteration** is caught by ComfyUI's execution engine and stops the queue. This is the clean way to signal "no more work."
- **Reset mechanism** — always provide a way to restart the counter. A boolean toggle is simplest.
- **Combinations list is cached** by hash. If the user changes available samplers/schedulers (e.g., installing a custom node), the list regenerates automatically.
- **Order matters.** `itertools.product` produces a deterministic order. Document it so users can predict which combination runs next.
- **Memory consideration** — each execution holds the latent in GPU memory. For large batches, consider `torch.cuda.empty_cache()` between iterations (or rely on ComfyUI's memory management).
- **Queue depth** — the user must queue enough runs to exhaust all combinations. Consider displaying the count in the UI so they know how many to enqueue.
- **Thread safety** — `_counter` is not atomic. This is fine because ComfyUI's execution engine is single-threaded per workflow run, but don't spawn additional threads that modify it.
