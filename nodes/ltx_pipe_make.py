"""
FW_LTXPipeMake — Bundles LTX 2.3 core components into a single LTX_PIPE wire.

This node eliminates "spaghetti wiring" by packaging the Model, VAE, CLIP,
Guider, Sampler, and Sigmas into one composite object that each FW_LTXScene
node can accept on a single input slot.
"""

import copy


class FW_LTXPipeMake:
    """Bundles LTX 2.3 core components (Model, VAE, CLIP, Guider, Sampler,
    Sigmas) into a single LTX_PIPE wire, keeping the canvas clean when
    chaining multiple scene nodes."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL", {
                    "tooltip": "LTX 2.3 diffusion model (e.g. ltx-2.3-22b-distilled)."
                }),
                "vae": ("VAE", {
                    "tooltip": "LTX Video VAE for encode / decode."
                }),
                "clip": ("CLIP", {
                    "tooltip": "Text encoder (Gemma 3 for LTX 2.3)."
                }),
                "guider": ("GUIDER", {
                    "tooltip": "STGGuiderAdvanced or equivalent guider node output."
                }),
                "sampler": ("SAMPLER", {
                    "tooltip": "Sampler algorithm (e.g. euler, euler_ancestral)."
                }),
                "sigmas": ("SIGMAS", {
                    "tooltip": "Noise schedule from LTXVScheduler (e.g. 4-step distilled)."
                }),
            }
        }

    RETURN_TYPES = ("LTX_PIPE",)
    RETURN_NAMES = ("ltx_pipe",)
    FUNCTION = "bundle"
    CATEGORY = "FrameWeaver/Scene"
    DESCRIPTION = (
        "Bundles LTX 2.3 core components into a single pipe wire so that "
        "you only need to connect one cable to each FW_LTXScene node."
    )

    def bundle(self, model, vae, clip, guider, sampler, sigmas):
        pipe = {
            "model": model,
            "vae": vae,
            "clip": clip,
            "guider": guider,
            "sampler": sampler,
            "sigmas": sigmas,
        }
        return (pipe,)
