"""
Dynamic Batch Splitter Node - ComfyUI Custom Node Example
Pattern: dynamic-outputs
Splits an image batch into individual outputs with dynamic count.
"""

import torch


class ImageBatchSplitter:
    """Split an image batch into individual outputs."""

    # Maximum possible outputs
    MAX_OUTPUTS = 64

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "count": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "dynamic": True,  # Triggers UI refresh when changed
                }),
            },
        }

    # Define maximum possible outputs
    RETURN_TYPES = tuple(["IMAGE"] * MAX_OUTPUTS)
    RETURN_NAMES = tuple([f"image_{i+1}" for i in range(MAX_OUTPUTS)])

    @classmethod
    def IS_DYNAMIC(cls):
        return True

    @classmethod
    def get_output_types(cls, **kwargs):
        count = int(kwargs.get("count", 1))
        return tuple(["IMAGE"] * count)

    @classmethod
    def get_output_names(cls, **kwargs):
        count = int(kwargs.get("count", 1))
        return [f"image_{i+1}" for i in range(count)]

    FUNCTION = "split"
    CATEGORY = "image/batch"
    DESCRIPTION = "Splits an image batch into individual outputs. Output count is dynamic based on the count parameter."
    SEARCH_ALIASES = ["batch", "split", "separate", "extract"]

    def split(self, images, count, **kwargs):
        batch_size = images.shape[0]
        results = []

        for i in range(count):
            if i < batch_size:
                # Extract single image from batch, keep batch dimension
                results.append(images[i:i+1])
            else:
                # Create blank image if batch is smaller than count
                blank = torch.zeros_like(images[0:1])
                results.append(blank)

        return tuple(results)


# Registration
NODE_CLASS_MAPPINGS = {
    "ImageBatchSplitter": ImageBatchSplitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageBatchSplitter": "Image Batch Splitter",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
