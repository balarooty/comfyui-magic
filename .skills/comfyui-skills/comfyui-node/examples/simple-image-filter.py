"""
Simple Image Filter Node - ComfyUI Custom Node Example
Pattern: simple-processor
Adjusts image brightness and contrast using torch operations.
"""

import torch


class ImageBrightness:
    """Adjust image brightness and contrast."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "brightness": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 3.0,
                    "step": 0.01,
                    "display": "slider"
                }),
                "contrast": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 3.0,
                    "step": 0.01,
                    "display": "slider"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "process"
    CATEGORY = "image/processing"
    DESCRIPTION = "Adjusts image brightness and contrast. Brightness multiplies pixel values, contrast adjusts around the midpoint."
    SEARCH_ALIASES = ["brightness", "contrast", "adjust", "lighten", "darken"]

    def process(self, image, brightness, contrast):
        # Apply brightness: multiply all pixel values
        result = image * brightness

        # Apply contrast: interpolate between midpoint (0.5) and pixel values
        midpoint = 0.5
        result = (result - midpoint) * contrast + midpoint

        # Clamp to valid range [0, 1]
        result = torch.clamp(result, 0.0, 1.0)

        return (result,)


# Registration
NODE_CLASS_MAPPINGS = {
    "ImageBrightness": ImageBrightness,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageBrightness": "Image Brightness/Contrast",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
