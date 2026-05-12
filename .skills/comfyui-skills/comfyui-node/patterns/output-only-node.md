# Output-Only Node

## When to Use

- Pure preview/display nodes that produce no downstream data
- Video players, image viewers, audio monitors
- Nodes that write files directly to disk without passing tensors downstream
- UI-only nodes that surface metadata, logs, or status

## Pattern

Set `OUTPUT_NODE = True` and `RETURN_TYPES = ()`. Return a dict with a `"ui"` key to send data to the frontend.

```python
import torch
import numpy as np
from PIL import Image
import folder_paths


class DualVideoPreview:
    """Displays two videos side-by-side in the ComfyUI viewer."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_a": ("IMAGE",),
                "images_b": ("IMAGE",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "preview"
    CATEGORY = "display"

    def preview(self, images_a, images_b, unique_id=None):
        # Convert tensors to numpy for frontend rendering
        results_a = []
        results_b = []

        for img_tensor in images_a:
            img_np = (255.0 * img_tensor.cpu().numpy()).astype(np.uint8)
            results_a.append(img_np)

        for img_tensor in images_b:
            img_np = (255.0 * img_tensor.cpu().numpy()).astype(np.uint8)
            results_b.append(img_np)

        return {
            "ui": {
                "images_a": results_a,
                "images_b": results_b,
            }
        }


NODE_CLASS_MAPPINGS = {
    "DualVideoPreview": DualVideoPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DualVideoPreview": "Dual Video Preview",
}
```

## Key Considerations

- `RETURN_TYPES = ()` means no downstream connections are possible.
- `OUTPUT_NODE = True` marks the node as a terminal node in the graph.
- Return `{"ui": {...}}` with JSON-serializable data (numpy arrays, strings, numbers). The frontend receives this in the `onExecuted` handler.
- Hidden inputs like `unique_id` and `prompt` are injected automatically by ComfyUI when declared in `"hidden"`.
- If you also need to save files, do it inside the `preview` method and include filenames in the `"ui"` dict so the frontend can reference them.
- Unlike returning tensors, UI data is not cached by the execution engine — the node re-executes every time its inputs change.
