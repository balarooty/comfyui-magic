# Template Tags

## When to Use

- Dynamic text overlays where the user references values from other nodes by title
- Logging and metadata that should include runtime values from the workflow
- Filename templates that adapt to the current configuration
- Any scenario where hardcoding node IDs is impractical and human-readable names are preferred

## Pattern

Parse the `PROMPT` hidden input to locate nodes by title. Replace `%Title.param%` tags with resolved values using regex.

```python
import re
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class TemplateTextNode:
    """Resolves %NodeTitle.param% tags at runtime using PROMPT data."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template": ("STRING", {
                    "default": "Steps: %KSampler.steps%, CFG: %KSampler.cfg",
                    "multiline": True,
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("resolved_text",)
    FUNCTION = "resolve"
    CATEGORY = "utils"

    # Matches %NodeTitle.param% — allows spaces in title
    TAG_PATTERN = re.compile(r"%([^%]+?)\.([^%]+?)%")

    def _build_title_index(self, prompt):
        """Build {node_title: {param: value}} lookup from PROMPT."""
        title_index = {}

        if prompt is None:
            return title_index

        for node_id, node_data in prompt.items():
            # "_meta" contains the human-readable title
            meta = node_data.get("_meta", {})
            title = meta.get("title", "")
            if not title:
                continue

            # Collect input values
            inputs = node_data.get("inputs", {})
            class_type = node_data.get("class_type", "")

            title_index[title] = {
                "class_type": class_type,
                **inputs,
            }

        return title_index

    def _resolve_tag(self, title, param, title_index):
        """Resolve a single %Title.param% tag."""
        node_data = title_index.get(title)
        if node_data is None:
            return f"%{title}.{param}%"  # unresolved — return as-is

        value = node_data.get(param)
        if value is None:
            return f"%{title}.{param}%"  # param not found

        # Handle different value types
        if isinstance(value, (list, tuple)):
            # Linked input — shows the connection reference
            return f"[linked:{param}]"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def resolve(self, template, prompt=None, extra_pnginfo=None):
        title_index = self._build_title_index(prompt)

        def replace_tag(match):
            title = match.group(1).strip()
            param = match.group(2).strip()
            return self._resolve_tag(title, param, title_index)

        resolved = self.TAG_PATTERN.sub(replace_tag, template)
        return (resolved,)


class TextOverlayWithTemplate:
    """Renders resolved template text onto images."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "text": ("STRING", {
                    "default": "Steps: %KSampler.steps%",
                    "multiline": True,
                }),
                "position": (["top-left", "top-right", "bottom-left", "bottom-right"], {
                    "default": "bottom-left",
                }),
                "font_size": ("INT", {"default": 24, "min": 8, "max": 256}),
            },
            "hidden": {
                "prompt": "PROMPT",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "overlay"
    CATEGORY = "image"

    def _resolve_template(self, template, prompt):
        """Inline tag resolution — same logic as TemplateTextNode."""
        if prompt is None:
            return template

        title_index = {}
        for node_id, node_data in prompt.items():
            meta = node_data.get("_meta", {})
            title = meta.get("title", "")
            if title:
                title_index[title] = {
                    **node_data.get("inputs", {}),
                    "class_type": node_data.get("class_type", ""),
                }

        tag_pattern = re.compile(r"%([^%]+?)\.([^%]+?)%")

        def replace(match):
            t = match.group(1).strip()
            p = match.group(2).strip()
            node = title_index.get(t)
            if node is None:
                return match.group(0)
            val = node.get(p)
            if val is None:
                return match.group(0)
            if isinstance(val, float):
                return f"{val:.2f}"
            return str(val)

        return tag_pattern.sub(replace, template)

    def overlay(self, images, text="Steps: %KSampler.steps%",
                position="bottom-left", font_size=24, prompt=None):

        resolved_text = self._resolve_template(text, prompt)
        result_frames = []

        for i in range(images.shape[0]):
            frame_np = (255.0 * images[i].cpu().numpy()).astype(np.uint8)
            pil_img = Image.fromarray(frame_np)
            draw = ImageDraw.Draw(pil_img)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except (IOError, OSError):
                font = ImageFont.load_default()

            # Measure text
            bbox = draw.textbbox((0, 0), resolved_text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            w, h = pil_img.size

            positions = {
                "top-left": (10, 10),
                "top-right": (w - tw - 10, 10),
                "bottom-left": (10, h - th - 10),
                "bottom-right": (w - tw - 10, h - th - 10),
            }
            pos = positions[position]

            # Shadow + text for readability
            draw.text((pos[0] + 1, pos[1] + 1), resolved_text, font=font, fill="black")
            draw.text(pos, resolved_text, font=font, fill="white")

            frame_np = np.array(pil_img).astype(np.float32) / 255.0
            result_frames.append(frame_np)

        import torch
        result = torch.from_numpy(np.stack(result_frames, axis=0)).float()
        return (result,)


NODE_CLASS_MAPPINGS = {
    "TemplateTextNode": TemplateTextNode,
    "TextOverlayWithTemplate": TextOverlayWithTemplate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TemplateTextNode": "Template Text",
    "TextOverlayWithTemplate": "Text Overlay with Template",
}
```

## Key Considerations

- **The `PROMPT` hidden input** is a dict keyed by node ID. Each value has `"class_type"`, `"inputs"`, and `"_meta": {"title": "..."}`.
- **Tags must match exact titles.** If the user renames a node from "KSampler" to "My Sampler", the tag `%KSampler.steps%` stops resolving. Consider fallback to `class_type` matching.
- **Linked inputs appear as lists** `[node_id, output_index]`, not scalars. Handle this gracefully — display "[linked]" or extract the upstream value by walking the prompt recursively.
- **Regex `%([^%]+?)\.([^%]+?)%`** allows spaces in titles. The lazy `+?` prevents greedy matching across multiple tags.
- **Return unresolved tags as-is** so the user can see which tags failed to match.
- **Float formatting** — use `f"{value:.2f}"` to avoid displaying `0.3333333333` for scheduler values.
- **Font paths** are platform-dependent. DejaVu is a safe Linux default; on macOS try `/System/Library/Fonts/Helvetica.ttc`. Fall back to `ImageFont.load_default()`.
- **Text shadow** (drawing text twice — black offset, white on top) is a cheap way to ensure readability on any background.
