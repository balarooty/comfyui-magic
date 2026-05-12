# Multi-Input Dynamic Count Pattern

## When to Use

Use this pattern when a node needs to accept a **variable number of inputs** at runtime. Common cases:

- Concatenating N images or tensors
- Merging multiple masks
- Blending an arbitrary number of layers
- Combining multiple conditioning tensors

ComfyUI's default `INPUT_TYPES` is static. To support dynamic input counts you combine a **widget** (`inputcount`) with `**kwargs` on `FUNCTION`, plus a small **JS extension** that adds "+" / "−" buttons to the node UI.

---

## Complete Python Code

```python
# nodes_image_concat_multi.py

import torch
import numpy as np
from PIL import Image


class ImageConcatMulti:
    """Concatenate N images along a chosen axis (horizontal or vertical)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "inputcount": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                "direction": (["right", "down"],),
            },
            "optional": {},  # Dynamic inputs added via JS extension
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "concat"
    CATEGORY = "image"

    def concat(self, inputcount, direction, **kwargs):
        images = []
        for i in range(inputcount):
            key = f"image_{i}"
            if key in kwargs and kwargs[key] is not None:
                img = kwargs[key]
                if isinstance(img, torch.Tensor):
                    images.append(img)
                elif isinstance(img, np.ndarray):
                    images.append(torch.from_numpy(img))
                else:
                    raise ValueError(f"Unsupported image type for {key}: {type(img)}")

        if not images:
            raise ValueError("No images provided to concatenate.")

        # Validate matching batch sizes
        batch = images[0].shape[0]
        for idx, img in enumerate(images):
            if img.shape[0] != batch:
                raise ValueError(
                    f"Batch size mismatch: image_0 has {batch}, image_{idx} has {img.shape[0]}"
                )

        # All images must share the same channel count
        channels = images[0].shape[-1]
        for idx, img in enumerate(images):
            if img.shape[-1] != channels:
                raise ValueError(
                    f"Channel mismatch: image_0 has {channels}, image_{idx} has {img.shape[-1]}"
                )

        if direction == "right":
            # Concatenate along width (dim=2)
            # First pad all images to the same height
            max_h = max(img.shape[1] for img in images)
            padded = []
            for img in images:
                if img.shape[1] < max_h:
                    pad_amount = max_h - img.shape[1]
                    pad = torch.zeros(
                        img.shape[0], pad_amount, img.shape[2], img.shape[3],
                        dtype=img.dtype, device=img.device
                    )
                    img = torch.cat([img, pad], dim=1)
                padded.append(img)
            result = torch.cat(padded, dim=2)
        else:
            # Concatenate along height (dim=1)
            max_w = max(img.shape[2] for img in images)
            padded = []
            for img in images:
                if img.shape[2] < max_w:
                    pad_amount = max_w - img.shape[2]
                    pad = torch.zeros(
                        img.shape[0], img.shape[1], pad_amount, img.shape[3],
                        dtype=img.dtype, device=img.device
                    )
                    img = torch.cat([img, pad], dim=2)
                padded.append(img)
            result = torch.cat(padded, dim=1)

        return (result,)


NODE_CLASS_MAPPINGS = {
    "ImageConcatMulti": ImageConcatMulti,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageConcatMulti": "Image Concat (Multi)",
}
```

---

## JavaScript Extension

```javascript
// js/image_concat_multi.js

import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "comfyui.image_concat_multi",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "ImageConcatMulti") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            this._imageCount = 0;
            this.addWidget("button", "+ Add Image", null, () => {
                this.addImageInput();
            });
            this.addWidget("button", "- Remove Image", null, () => {
                this.removeImageInput();
            });

            // Add initial inputs
            this.addImageInput();
            this.addImageInput();

            return r;
        };

        nodeType.prototype.addImageInput = function () {
            const index = this._imageCount;
            const name = `image_${index}`;
            this.addInput(name, "IMAGE");
            this._imageCount++;

            // Sync the inputcount widget
            this.syncInputCountWidget();
        };

        nodeType.prototype.removeImageInput = function () {
            if (this._imageCount <= 2) return; // keep at least 2

            this._imageCount--;
            const name = `image_${this._imageCount}`;
            this.removeInput(this.findInputSlot(name));

            this.syncInputCountWidget();
        };

        nodeType.prototype.syncInputCountWidget = function () {
            const widget = this.widgets.find((w) => w.name === "inputcount");
            if (widget) {
                widget.value = this._imageCount;
            }
        };
    },

    onNodeCreated(node) {
        // When loading a workflow, restore dynamic inputs from inputcount
        if (node.type === "ImageConcatMulti") {
            const countWidget = node.widgets.find((w) => w.name === "inputcount");
            if (countWidget) {
                const count = countWidget.value;
                while (node._imageCount < count) {
                    node.addImageInput();
                }
            }
        }
    },
});
```

---

## Key Considerations

| Concern | Guidance |
|---|---|
| **Naming convention** | Dynamic inputs must follow a predictable pattern (`image_0`, `image_1`, …). Use a loop with `f"image_{i}"` to retrieve them in `FUNCTION`. |
| **`**kwargs`** | The function **must** accept `**kwargs` because static `INPUT_TYPES` cannot list the dynamic inputs. |
| **Widget sync** | The `inputcount` widget value must stay in sync with the actual number of inputs. The JS extension calls `syncInputCountWidget()` after every add/remove. |
| **Workflow serialization** | When a workflow is saved, ComfyUI serializes only widget values and link connections. On reload, the JS `onNodeCreated` reads `inputcount` and re-creates the inputs. |
| **Min/Max bounds** | Enforce a minimum (usually 2) and maximum (e.g., 20) both in the Python widget definition and in the JS guard (`if (this._imageCount <= 2) return`). |
| **Validation** | Always validate that `kwargs` contains the expected keys before processing. Missing inputs should raise a clear error. |
| **Edge padding** | When concatenating tensors of different sizes, pad to a common dimension (see the `padded` logic above). |

---

## Variations

### 1. Model Stack

```python
# Stack N models into a list for batch processing
class ModelStack:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "inputcount": ("INT", {"default": 2, "min": 2, "max": 10, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("MODEL_LIST",)
    FUNCTION = "stack"
    CATEGORY = "model"

    def stack(self, inputcount, **kwargs):
        models = [kwargs[f"model_{i}"] for i in range(inputcount) if f"model_{i}" in kwargs]
        return (models,)
```

### 2. Weighted Blend

Combine N images with per-image weight sliders:

```python
# Add a dynamic FLOAT widget alongside each image input
# JS: this.addInput(name, "IMAGE"); this.addWidget("number", `weight_${index}`, 1.0, ...);
```

### 3. Conditioning Merge

```python
# Merge N conditioning tensors
class ConditioningMergeMulti:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "inputcount": ("INT", {"default": 2, "min": 2, "max": 10, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "merge"
    CATEGORY = "conditioning"

    def merge(self, inputcount, **kwargs):
        conds = [kwargs[f"conditioning_{i}"] for i in range(inputcount) if f"conditioning_{i}" in kwargs]
        # Merge logic: concatenate prompt strings or combine tensors
        merged = []
        for c in conds:
            merged.extend(c)
        return (merged,)
```

### 4. No JavaScript (Pure Python)

If you only need a small range (e.g., 2–4 inputs), you can define all optional inputs statically and ignore unused ones:

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "image_1": ("IMAGE",),
            "image_2": ("IMAGE",),
        },
        "optional": {
            "image_3": ("IMAGE",),
            "image_4": ("IMAGE",),
        },
    }
```

This avoids JS entirely but has a fixed upper bound.
