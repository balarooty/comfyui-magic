"""
FrameWeaver — LTX 2.3 Multi-Scene Video Generation Nodes
=========================================================

Custom node pack for ComfyUI that provides a user-friendly chained pipeline
for generating multi-scene videos with LTX 2.3.

Nodes
-----
* **FW_LTXPipeMake**  — Bundles Model / VAE / CLIP / Guider / Sampler /
  Sigmas into a single ``LTX_PIPE`` wire.
* **FW_LTXScene**     — Generates one video scene.  Wire the previous
  scene's ``last_frame`` into ``reference_image`` for I2V continuity.
* **FW_VideoBatcher** — Concatenates multiple scene outputs into one
  continuous video for saving.

Installation
------------
Place this folder inside ``ComfyUI/custom_nodes/`` and restart ComfyUI.
Requires the **ComfyUI-LTXVideo** pack from Lightricks for full
functionality (falls back to built-in LTX nodes otherwise).
"""

from .nodes.ltx_pipe_make import FW_LTXPipeMake
from .nodes.ltx_scene import FW_LTXScene
from .nodes.video_batcher import FW_VideoBatcher

# ── ComfyUI Registration ────────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "FW_LTXPipeMake": FW_LTXPipeMake,
    "FW_LTXScene": FW_LTXScene,
    "FW_VideoBatcher": FW_VideoBatcher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FW_LTXPipeMake": "🎬 FW LTX Pipe Make",
    "FW_LTXScene": "🎬 FW LTX Scene",
    "FW_VideoBatcher": "🎬 FW Video Batcher",
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]
