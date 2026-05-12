"""
LoRA Stacker Node - ComfyUI Custom Node Example
Pattern: multi-input with **kwargs
Applies multiple LoRAs with individual strengths using dynamic inputs.
"""

import folder_paths
import comfy.sd
import comfy.utils


class LoRAStacker:
    """Apply multiple LoRAs with individual strength controls."""

    @classmethod
    def INPUT_TYPES(s):
        lora_list = folder_paths.get_filename_list("loras")
        if len(lora_list) == 0:
            lora_list = ["none"]

        required = {
            "model": ("MODEL",),
            "clip": ("CLIP",),
            "num_loras": ("INT", {
                "default": 1,
                "min": 1,
                "max": 10,
                "step": 1,
                "tooltip": "Number of LoRAs to stack"
            }),
        }

        # Pre-define max LoRA slots as optional inputs
        optional = {}
        for i in range(1, 11):
            optional[f"lora_name_{i}"] = (lora_list, {"default": "none"})
            optional[f"strength_model_{i}"] = ("FLOAT", {
                "default": 1.0,
                "min": -10.0,
                "max": 10.0,
                "step": 0.01,
            })
            optional[f"strength_clip_{i}"] = ("FLOAT", {
                "default": 1.0,
                "min": -10.0,
                "max": 10.0,
                "step": 0.01,
            })

        return {"required": required, "optional": optional}

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    FUNCTION = "stack"
    CATEGORY = "loaders/lora"
    DESCRIPTION = "Stacks multiple LoRAs with individual model and clip strengths. LoRAs are applied in order."
    SEARCH_ALIASES = ["lora", "stack", "multiple lora", "lora chain"]

    def stack(self, model, clip, num_loras, **kwargs):
        model_out = model.clone()
        clip_out = clip.clone()

        applied_count = 0

        for i in range(1, num_loras + 1):
            lora_name = kwargs.get(f"lora_name_{i}", "none")
            strength_model = kwargs.get(f"strength_model_{i}", 1.0)
            strength_clip = kwargs.get(f"strength_clip_{i}", 1.0)

            if lora_name == "none" or lora_name is None:
                continue

            lora_path = folder_paths.get_full_path("loras", lora_name)
            if lora_path is None:
                print(f"[LoRAStacker] Warning: LoRA '{lora_name}' not found, skipping")
                continue

            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            model_out, clip_out = comfy.sd.load_lora_for_models(
                model_out, clip_out, lora, strength_model, strength_clip
            )
            applied_count += 1
            print(f"[LoRAStacker] Applied LoRA {i}: {lora_name} "
                  f"(model={strength_model}, clip={strength_clip})")

        print(f"[LoRAStacker] Total LoRAs applied: {applied_count}")
        return (model_out, clip_out)


# Registration
NODE_CLASS_MAPPINGS = {
    "LoRAStacker": LoRAStacker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoRAStacker": "LoRA Stacker",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
