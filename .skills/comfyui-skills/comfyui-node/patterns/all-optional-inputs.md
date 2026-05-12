# All Optional Inputs

## When to Use

- Nodes that can run with zero connections — pure preview, config generators, or constant producers
- Display nodes that show defaults when nothing is connected
- Utility nodes that synthesize data from internal state rather than upstream tensors
- Very rare pattern; most nodes have at least one required input

## Pattern

Declare every input inside `"optional"`. The node executes with no wires attached.

```python
import random
import folder_paths


class DualVideoCompare:
    """Compare two video sources — each input is optional, defaults to a placeholder."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "video_a": ("IMAGE",),
                "video_b": ("IMAGE",),
                "label_a": ("STRING", {
                    "default": "Source A",
                    "multiline": False,
                }),
                "label_b": ("STRING", {
                    "default": "Source B",
                    "multiline": False,
                }),
                "blend_mode": (["side-by-side", "overlay", "difference", "swipe"], {
                    "default": "side-by-side",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("composited", "info")
    FUNCTION = "compare"
    CATEGORY = "display"

    def compare(self, video_a=None, video_b=None,
                label_a="Source A", label_b="Source B",
                blend_mode="side-by-side"):

        info_lines = []

        if video_a is None and video_b is None:
            # Nothing connected — produce a blank frame as placeholder
            import torch
            placeholder = torch.zeros(1, 64, 64, 3)
            info_lines.append("No inputs connected. Showing placeholder.")
            return (placeholder, "\n".join(info_lines))

        if video_a is None:
            video_a = video_b
            info_lines.append(f"video_a missing — mirroring {label_b}")
        elif video_b is None:
            video_b = video_a
            info_lines.append(f"video_b missing — mirroring {label_a}")

        # Frame count must match; truncate to shortest
        count = min(video_a.shape[0], video_b.shape[0])
        a = video_a[:count]
        b = video_b[:count]
        info_lines.append(f"Comparing {count} frames, mode={blend_mode}")
        info_lines.append(f"Label A: {label_a}")
        info_lines.append(f"Label B: {label_b}")

        if blend_mode == "side-by-side":
            composited = torch.cat([a, b], dim=2)  # concat along width
        elif blend_mode == "difference":
            composited = (a - b).abs()
        elif blend_mode == "overlay":
            composited = (a * 0.5 + b * 0.5).clamp(0, 1)
        else:  # swipe — left half A, right half B
            mid = a.shape[2] // 2
            composited = a.clone()
            composited[:, :, mid:, :] = b[:, :, mid:, :]

        return (composited, "\n".join(info_lines))


NODE_CLASS_MAPPINGS = {
    "DualVideoCompare": DualVideoCompare,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DualVideoCompare": "Dual Video Compare",
}
```

## Key Considerations

- All inputs live under `"optional"` — none under `"required"`.
- When nothing is connected, every parameter receives its default value (`None` for tensors, declared default for scalars).
- Always guard against `None` tensors before operating on them. Returning a placeholder or raising a clear error is better than a cryptic crash.
- Optional tensor inputs that are `None` at runtime mean the user did not wire that port — not that the upstream node returned `None`.
- This pattern is rare. Most nodes should have at least one required input to make their purpose clear.
- Optional inputs still support type constraints (`"IMAGE"`, `"STRING"`, etc.) and widget overrides (`"default"`, `"multiline"`).
- If you combine optional inputs with `OUTPUT_NODE = True`, you get a fully autonomous preview node that works out of the box.
