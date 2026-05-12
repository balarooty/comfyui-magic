import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TAG_PATTERN = re.compile(r"%([\w]+)\.([\w]+)%")


class TemplateTagOverlay:
    """Overlays text on images using %NodeTitle.param% template tags resolved from the prompt graph."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "template": ("STRING", {
                    "multiline": True,
                    "default": "Seed: %KSampler.seed%\nSteps: %KSampler.steps%",
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "overlay"
    CATEGORY = "image"

    @classmethod
    def IS_CHANGED(cls, images, template, prompt=None, extra_pnginfo=None):
        return float("nan")

    def _resolve_tag(self, title: str, param: str, prompt: dict) -> str:
        if not prompt:
            return f"%{title}.{param}%"
        for node_id, node_data in prompt.items():
            meta = node_data.get("_meta", {})
            if meta.get("title") == title:
                inputs = node_data.get("inputs", {})
                if param in inputs:
                    return str(inputs[param])
        return f"%{title}.{param}%"

    def overlay(self, images, template, prompt=None, extra_pnginfo=None):
        resolved = TAG_PATTERN.sub(
            lambda m: self._resolve_tag(m.group(1), m.group(2), prompt or {}), template
        )

        result = []
        for img_tensor in images:
            img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np)
            draw = ImageDraw.Draw(pil_img)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except (IOError, OSError):
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), resolved, font=font)
            text_h = bbox[3] - bbox[1]
            y = pil_img.height - text_h - 10

            draw.rectangle(
                [(0, y - 4), (pil_img.width, pil_img.height)],
                fill=(0, 0, 0, 180),
            )
            draw.text((10, y), resolved, fill=(255, 255, 255), font=font)

            result.append(np.array(pil_img).astype(np.float32) / 255.0)

        import torch
        return (torch.from_numpy(np.stack(result)),)


NODE_CLASS_MAPPINGS = {
    "TemplateTagOverlay": TemplateTagOverlay,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TemplateTagOverlay": "Template Tag Overlay",
}
