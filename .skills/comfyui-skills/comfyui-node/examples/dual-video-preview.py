import hashlib
import os
import folder_paths

OUTPUT_NODE = True


class DualVideoPreview:
    """Compare two videos side-by-side in the UI. Accepts file paths or frame tensors."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "video_1": ("STRING", {"default": ""}),
                "video_2": ("STRING", {"default": ""}),
                "frames_1": ("IMAGE",),
                "frames_2": ("IMAGE",),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "preview"
    CATEGORY = "video"

    @classmethod
    def IS_CHANGED(cls, video_1="", video_2="", frames_1=None, frames_2=None, fps=24):
        parts = [video_1, video_2, str(fps)]
        if frames_1 is not None:
            parts.append(frames_1.cpu().numpy().tobytes().hex()[:64])
        if frames_2 is not None:
            parts.append(frames_2.cpu().numpy().tobytes().hex()[:64])
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def preview(self, video_1="", video_2="", frames_1=None, frames_2=None, fps=24):
        import torch
        import numpy as np
        from PIL import Image

        output_dir = folder_paths.get_temp_directory()
        os.makedirs(output_dir, exist_ok=True)

        paths = []
        for idx, (path, frames) in enumerate(
            [(video_1, frames_1), (video_2, frames_2)], start=1
        ):
            if path and os.path.isfile(path):
                paths.append(path)
            elif frames is not None:
                frames_np = (frames.cpu().numpy() * 255).astype(np.uint8)
                h, w = frames_np.shape[1], frames_np.shape[2]
                content = frames_np.tobytes() + f"{fps}".encode()
                digest = hashlib.sha256(content).hexdigest()[:16]
                out_path = os.path.join(output_dir, f"dual_preview_{idx}_{digest}.webp")
                if not os.path.exists(out_path):
                    imgs = [Image.fromarray(f) for f in frames_np]
                    imgs[0].save(
                        out_path,
                        save_all=True,
                        append_images=imgs[1:],
                        duration=int(1000 / fps),
                        loop=0,
                    )
                paths.append(out_path)
            else:
                paths.append("")

        return {"ui": {"video_paths": paths}}


NODE_CLASS_MAPPINGS = {
    "DualVideoPreview": DualVideoPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DualVideoPreview": "Dual Video Preview",
}
