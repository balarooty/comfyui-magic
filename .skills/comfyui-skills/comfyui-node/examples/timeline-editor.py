"""
Timeline Editor Node - ComfyUI Custom Node Example
Pattern: web-widget
Visual timeline editor for prompt scheduling with custom JS widget.
"""

import json


class TimelineEditor:
    """Visual timeline editor for prompt scheduling."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "num_segments": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 20,
                    "step": 1,
                }),
                "total_frames": ("INT", {
                    "default": 120,
                    "min": 1,
                    "max": 10000,
                    "step": 1,
                }),
            },
            "hidden": {
                "timeline_data": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("prompts", "segment_lengths", "fps")
    FUNCTION = "process"
    CATEGORY = "conditioning/scheduling"
    DESCRIPTION = "Visual timeline editor for creating prompt schedules. Edit segments in the node widget."
    SEARCH_ALIASES = ["timeline", "schedule", "prompt schedule", "timeline editor"]

    def process(self, num_segments, total_frames, timeline_data="", unique_id=""):
        # Parse timeline data from JS widget
        if timeline_data and timeline_data.strip():
            try:
                data = json.loads(timeline_data)
            except json.JSONDecodeError:
                data = self._default_data(num_segments, total_frames)
        else:
            data = self._default_data(num_segments, total_frames)

        segments = data.get("segments", [])
        prompts = []
        segment_lengths = []

        for seg in segments:
            prompts.append(seg.get("prompt", ""))
            segment_lengths.append(str(seg.get("frames", 0)))

        # Join with pipe separator
        prompts_str = " | ".join(prompts)
        lengths_str = ", ".join(segment_lengths)

        return (prompts_str, lengths_str, float(data.get("fps", 24)))

    def _default_data(self, num_segments, total_frames):
        frames_per_segment = max(1, total_frames // num_segments)
        segments = []
        for i in range(num_segments):
            frames = frames_per_segment
            if i == num_segments - 1:
                # Last segment gets remaining frames
                frames = total_frames - (frames_per_segment * (num_segments - 1))
            segments.append({
                "prompt": f"segment {i + 1}",
                "frames": frames,
                "color": f"hsl({(i * 360) // num_segments}, 70%, 50%)",
            })
        return {"segments": segments, "fps": 24}


# Registration
NODE_CLASS_MAPPINGS = {
    "TimelineEditor": TimelineEditor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TimelineEditor": "Timeline Editor",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
