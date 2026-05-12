"""
Custom Noise Generator Node - ComfyUI Custom Node Example
Pattern: sampler-node
Generates custom noise patterns for sampling.
"""

import torch
import math


class CustomNoiseGenerator:
    """Generate custom noise patterns for diffusion sampling."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latent": ("LATENT",),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xFFFFFFFFFFFFFFFF,
                    "control_after_generate": True,
                }),
                "noise_type": (["uniform", "gaussian", "perlin"], {
                    "default": "gaussian",
                }),
                "scale": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.01,
                }),
            },
        }

    RETURN_TYPES = ("NOISE",)
    RETURN_NAMES = ("noise",)
    FUNCTION = "generate"
    CATEGORY = "sampling/noise"
    DESCRIPTION = "Generates custom noise patterns. Supports uniform, gaussian, and perlin noise."
    SEARCH_ALIASES = ["noise", "generator", "random", "perlin"]

    def generate(self, latent, seed, noise_type, scale):
        generator = torch.manual_seed(seed)
        latent_tensor = latent["samples"]
        shape = latent_tensor.shape

        if noise_type == "uniform":
            noise = torch.rand(shape, generator=generator) * 2 - 1
        elif noise_type == "gaussian":
            noise = torch.randn(shape, generator=generator)
        elif noise_type == "perlin":
            noise = self._perlin_noise(shape, seed)
        else:
            noise = torch.randn(shape, generator=generator)

        noise = noise * scale

        return (CustomNoise(noise, seed),)

    def _perlin_noise(self, shape, seed):
        """Generate Perlin-like noise using frequency-based approach."""
        torch.manual_seed(seed)
        b, c, h, w = shape

        noise = torch.zeros(shape)
        octaves = 4
        persistence = 0.5

        for octave in range(octaves):
            freq = 2 ** octave
            amp = persistence ** octave

            # Generate random phase-shifted sine waves
            h_freq = max(1, h // freq)
            w_freq = max(1, w // freq)

            low_res = torch.randn(b, c, h_freq, w_freq)
            # Upsample to full resolution
            upsampled = torch.nn.functional.interpolate(
                low_res, size=(h, w), mode="bilinear", align_corners=False
            )
            noise += upsampled * amp

        # Normalize to [-1, 1]
        noise = noise / noise.abs().max()
        return noise


class CustomNoise:
    """Custom noise object implementing the NOISE interface."""

    def __init__(self, noise_tensor, seed):
        self.noise = noise_tensor
        self._seed = seed

    @property
    def seed(self):
        return self._seed

    def generate_noise(self, input_latent, seed_override=None):
        if seed_override is not None and seed_override != self._seed:
            # Regenerate with new seed
            generator = torch.manual_seed(seed_override)
            return torch.randn_like(self.noise, generator=generator) * self.noise.abs().mean()
        return self.noise.clone()


# Registration
NODE_CLASS_MAPPINGS = {
    "CustomNoiseGenerator": CustomNoiseGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CustomNoiseGenerator": "Custom Noise Generator",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
