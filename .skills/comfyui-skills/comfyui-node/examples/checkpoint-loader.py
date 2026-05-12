"""
Checkpoint Loader Node - ComfyUI Custom Node Example
Pattern: model-loader
Loads a checkpoint file and extracts MODEL, CLIP, and VAE components.
"""

import hashlib
import os

import folder_paths
import comfy.sd
import comfy.utils


class CustomCheckpointLoader:
    """Load a checkpoint and extract its components."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "ckpt_name": (folder_paths.get_filename_list("checkpoints"), {
                    "tooltip": "The checkpoint file to load."
                }),
            },
            "optional": {
                "custom_name": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Optional custom name for logging"
                }),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("model", "clip", "vae")
    FUNCTION = "load"
    CATEGORY = "loaders"
    DESCRIPTION = "Loads a checkpoint file and splits it into MODEL, CLIP, and VAE components."
    SEARCH_ALIASES = ["checkpoint", "model loader", "safetensors"]

    @classmethod
    def IS_CHANGED(s, ckpt_name, custom_name=""):
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        if not os.path.exists(ckpt_path):
            return float("NaN")
        m = hashlib.sha256()
        with open(ckpt_path, "rb") as f:
            m.update(f.read())
        return m.digest().hex()

    def load(self, ckpt_name, custom_name=""):
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        if not os.path.exists(ckpt_path):
            raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

        print(f"[CustomCheckpointLoader] Loading: {custom_name or ckpt_name}")

        # Load checkpoint
        out = comfy.sd.load_checkpoint_guess_config(
            ckpt_path,
            output_vae=True,
            output_clip=True,
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
        )

        model = out[0]
        clip = out[1]
        vae = out[2]

        return (model, clip, vae)


# Registration
NODE_CLASS_MAPPINGS = {
    "CustomCheckpointLoader": CustomCheckpointLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CustomCheckpointLoader": "Custom Checkpoint Loader",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
