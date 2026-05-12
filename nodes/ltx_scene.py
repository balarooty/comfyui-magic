"""
FW_LTXScene — Generates a single LTX 2.3 video scene.

Core behaviour
--------------
* If ``reference_image`` is connected, uses Image-to-Video mode so the
  generated scene starts from that exact frame.
* If nothing is connected, falls back to Text-to-Video mode (pure noise).
* Outputs the decoded ``video_frames``, a ``last_frame`` image that should be
  wired into the next scene's ``reference_image`` input, and the raw
  ``latent`` for optional downstream processing.
* The ``ltx_pipe`` is passed through unchanged so you can daisy-chain scenes.

Scene Bridging
--------------
Scene 1's ``last_frame`` → Scene 2's ``reference_image`` → …  
This guarantees visual continuity: every scene starts exactly where the
previous one ended.
"""

import copy
import sys
import os
import torch

# ---------------------------------------------------------------------------
# Safe import of LTXVBaseSampler from the Lightricks custom-node pack.
# The pack may live at any ComfyUI custom_nodes path, so we resolve it at
# import time and give a clear error if it is missing.
# ---------------------------------------------------------------------------
_LTXV_BASE_SAMPLER_CLS = None


def _resolve_ltxv_base_sampler():
    """Lazy-import so the module can at least *load* even when the Lightricks
    pack is not installed (ComfyUI will still register the other nodes)."""
    global _LTXV_BASE_SAMPLER_CLS
    if _LTXV_BASE_SAMPLER_CLS is not None:
        return _LTXV_BASE_SAMPLER_CLS

    try:
        # ComfyUI adds custom_nodes/* to sys.path, so direct import works
        # when ComfyUI-LTXVideo is installed.
        from ComfyUI_LTXVideo.easy_samplers import LTXVBaseSampler  # type: ignore
        _LTXV_BASE_SAMPLER_CLS = LTXVBaseSampler
    except ImportError:
        try:
            # Fallback: try the hyphenated folder name variant
            # ComfyUI normalises hyphens → underscores, but just in case.
            import importlib
            mod = importlib.import_module("ComfyUI-LTXVideo.easy_samplers")
            _LTXV_BASE_SAMPLER_CLS = mod.LTXVBaseSampler
        except (ImportError, ModuleNotFoundError):
            _LTXV_BASE_SAMPLER_CLS = None

    return _LTXV_BASE_SAMPLER_CLS


class FW_LTXScene:
    """Generates one video scene with LTX 2.3.

    * Wire ``reference_image`` from the previous scene's ``last_frame`` to
      achieve I2V continuity.
    * Wire ``ltx_pipe`` through from scene to scene — it passes through
      unchanged.
    * The ``last_frame`` output is the final decoded frame of this scene,
      ready to be fed into the next scene's ``reference_image``.
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "ltx_pipe": ("LTX_PIPE", {
                    "tooltip": "Bundled LTX components from FW_LTXPipeMake."
                }),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "A cinematic shot of a sunset over the ocean",
                    "tooltip": "Text prompt describing this scene."
                }),
                "negative_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Negative prompt (things to avoid)."
                }),
                "frames": ("INT", {
                    "default": 33,
                    "min": 9,
                    "max": 257,
                    "step": 8,
                    "tooltip": (
                        "Number of video frames to generate for this scene. "
                        "Must follow the 8k+1 rule (9, 17, 25, 33 … 257)."
                    ),
                }),
                "width": ("INT", {
                    "default": 768,
                    "min": 64,
                    "max": 2048,
                    "step": 32,
                    "tooltip": "Output width in pixels."
                }),
                "height": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 2048,
                    "step": 32,
                    "tooltip": "Output height in pixels."
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xFFFFFFFFFFFFFFFF,
                    "tooltip": "Random seed for this scene."
                }),
                "cond_strength": ("FLOAT", {
                    "default": 0.9,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": (
                        "How strongly the reference image conditions the "
                        "generation.  Higher = closer match to reference."
                    ),
                }),
            },
            "optional": {
                "reference_image": ("IMAGE", {
                    "tooltip": (
                        "Connect the 'last_frame' output from the previous "
                        "FW_LTXScene here.  For the very first scene this can "
                        "be any starting image, or left empty for T2V mode."
                    ),
                }),
            },
        }

    RETURN_TYPES = ("LTX_PIPE", "IMAGE", "IMAGE", "LATENT")
    RETURN_NAMES = ("ltx_pipe", "video_frames", "last_frame", "latent")
    FUNCTION = "generate"
    CATEGORY = "FrameWeaver/Scene"
    DESCRIPTION = (
        "Generates a single LTX 2.3 video scene.  Wire the previous scene's "
        "'last_frame' into 'reference_image' for seamless transitions."
    )

    # ------------------------------------------------------------------
    # Main generation method
    # ------------------------------------------------------------------
    def generate(
        self,
        ltx_pipe,
        prompt,
        negative_prompt,
        frames,
        width,
        height,
        seed,
        cond_strength,
        reference_image=None,
    ):
        # ---- 0. Unpack the pipe ----
        model = ltx_pipe["model"]
        vae = ltx_pipe["vae"]
        clip = ltx_pipe["clip"]
        guider = ltx_pipe["guider"]
        sampler = ltx_pipe["sampler"]
        sigmas = ltx_pipe["sigmas"]

        # ---- 1. Encode prompts ----
        pos_tokens = clip.tokenize(prompt)
        positive = clip.encode_from_tokens_scheduled(pos_tokens)

        neg_text = negative_prompt if negative_prompt else ""
        neg_tokens = clip.tokenize(neg_text)
        negative = clip.encode_from_tokens_scheduled(neg_tokens)

        # ---- 2. Prepare guider with this scene's conditioning ----
        scene_guider = copy.copy(guider)
        scene_guider.original_conds = copy.deepcopy(guider.original_conds)
        scene_guider.set_conds(positive, negative)

        # ---- 3. Prepare noise ----
        # ComfyUI's Noise_RandomNoise is the standard noise provider
        try:
            from comfy_extras.nodes_custom_sampler import Noise_RandomNoise
            noise = Noise_RandomNoise(seed)
        except ImportError:
            # Fallback for older ComfyUI versions
            import comfy.sample
            noise = comfy.sample.prepare_noise(seed)

        # ---- 4. Generate with LTXVBaseSampler ----
        LTXVBaseSampler = _resolve_ltxv_base_sampler()

        if LTXVBaseSampler is not None:
            # Use the official Lightricks sampler
            sampler_node = LTXVBaseSampler()
            latent, out_pos, out_neg = sampler_node.sample(
                model=model,
                vae=vae,
                width=width,
                height=height,
                num_frames=frames,
                guider=scene_guider,
                sampler=sampler,
                sigmas=sigmas,
                noise=noise,
                optional_cond_images=reference_image,
                optional_cond_indices="0" if reference_image is not None else None,
                strength=cond_strength,
            )
        else:
            # Fallback: use ComfyUI's built-in LTX sampling path
            latent = self._fallback_generate(
                model, vae, clip,
                positive, negative,
                width, height, frames, seed,
                reference_image, cond_strength,
                sampler, sigmas, noise,
            )

        # ---- 5. Decode latent → pixel frames ----
        video_frames = vae.decode(latent["samples"])

        # ---- 6. Extract last frame for chaining ----
        # ComfyUI IMAGE tensor shape: [N, H, W, C]
        last_frame = video_frames[-1:].clone()

        # ---- 7. Pass pipe through unchanged ----
        return (ltx_pipe, video_frames, last_frame, latent)

    # ------------------------------------------------------------------
    # Fallback generator when ComfyUI-LTXVideo is not installed
    # ------------------------------------------------------------------
    def _fallback_generate(
        self, model, vae, clip,
        positive, negative,
        width, height, frames, seed,
        reference_image, cond_strength,
        sampler_obj, sigmas, noise,
    ):
        """Generate using ComfyUI's built-in LTX nodes (available in core
        since LTX-2 was merged upstream)."""
        import comfy.sample
        from comfy_extras.nodes_lt import EmptyLTXVLatentVideo

        # Create empty latent
        latent = EmptyLTXVLatentVideo().execute(width, height, frames, 1)[0]

        # If a reference image is provided, encode it into the first frame
        if reference_image is not None:
            # Resize to target dimensions
            import comfy.utils
            ref = comfy.utils.common_upscale(
                reference_image.movedim(-1, 1),
                width, height, "bilinear", crop="center",
            ).movedim(1, -1).clamp(0, 1)

            # Encode first frame
            encoded = vae.encode(ref[:1])
            latent["samples"][:, :, :encoded.shape[2]] = encoded

            # Create noise mask protecting the reference frame
            noise_mask = torch.ones(
                (1, 1, latent["samples"].shape[2], 1, 1),
                dtype=torch.float32,
                device=latent["samples"].device,
            )
            noise_mask[:, :, :encoded.shape[2]] = 1.0 - cond_strength
            latent["noise_mask"] = noise_mask

        # Use ComfyUI's SamplerCustomAdvanced for the denoising pass
        from comfy_extras.nodes_custom_sampler import SamplerCustomAdvanced

        # Build a basic guider from the conditionings
        from comfy_extras.nodes_custom_sampler import Guider_Basic
        basic_guider = Guider_Basic()
        guider_obj = basic_guider.get_guider(model, positive)[0]

        _, denoised = SamplerCustomAdvanced().sample(
            noise=noise,
            guider=guider_obj,
            sampler=sampler_obj,
            sigmas=sigmas,
            latent_image=latent,
        )

        return denoised
