"""
FW_VideoBatcher — Concatenates multiple video segments into one continuous
IMAGE tensor for saving with VHS_VideoCombine or any video output node.

Accepts up to 10 optional video inputs (``video_1`` through ``video_10``).
Only connected inputs are concatenated; disconnected slots are ignored.
"""

import torch


class FW_VideoBatcher:
    """Concatenates multiple IMAGE-batch video segments along the batch
    (frame) dimension.

    Plug each FW_LTXScene's ``video_frames`` output into consecutive
    ``video_N`` inputs.  The node concatenates them in order and outputs
    a single IMAGE tensor ready for VHS_VideoCombine or PreviewVideo.
    """

    @classmethod
    def INPUT_TYPES(s):
        inputs = {"required": {}, "optional": {}}
        for i in range(1, 11):
            inputs["optional"][f"video_{i}"] = ("IMAGE", {
                "tooltip": f"Video segment {i} (connect from FW_LTXScene video_frames)."
            })
        return inputs

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("combined_video", "total_frames")
    FUNCTION = "batch"
    CATEGORY = "FrameWeaver/Scene"
    DESCRIPTION = (
        "Concatenates up to 10 video segments into a single continuous "
        "IMAGE tensor.  Connect each FW_LTXScene's 'video_frames' output "
        "to the video_1 … video_10 inputs in scene order."
    )

    def batch(self, **kwargs):
        videos = []
        for i in range(1, 11):
            key = f"video_{i}"
            if key in kwargs and kwargs[key] is not None:
                videos.append(kwargs[key])

        if not videos:
            # Return a 1-frame black image as a safe fallback
            empty = torch.zeros(1, 64, 64, 3)
            return (empty, 0)

        combined = torch.cat(videos, dim=0)
        total_frames = combined.shape[0]
        return (combined, total_frames)
