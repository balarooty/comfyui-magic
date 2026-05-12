# Sampler Node Pattern

## When to Use

Use this pattern for custom noise generation, custom sampler logic, or sigma schedule manipulation. This is an advanced pattern that interfaces directly with ComfyUI's sampling pipeline. You typically combine NOISE, SAMPLER, and SIGMAS objects to control how denoising is performed.

**Typical use cases:**
- Custom noise generators (frequency-aware noise, noise from image)
- Custom sampling schedules (custom sigma curves)
- Custom sampler algorithms (modified Euler, custom solver)
- Noise blending and manipulation
- Sampler parameter scheduling

## Architecture

```
NOISE generator + SAMPLER + SIGMAS → KSampler → denoised latent
      ↓                ↓              ↓
noise_gen()      sample()      sigma schedule
```

The sampling pipeline:
1. **NOISE** generates initial noise in latent space
2. **SIGMAS** defines the noise schedule (sigma values per step)
3. **SAMPLER** executes the denoising loop using the model

## Key Concepts

| Concept | Detail |
|---|---|
| NOISE | Object with `generate_noise(latent)` method returning noise tensor |
| SAMPLER | Object with `sample(model, sigmas, ...)` method |
| SIGMAS | 1D tensor of sigma values defining the noise schedule |
| latent tensor | Shape `[B, C, H, W]` in latent space (4× smaller than pixel space) |
| sigma | Noise level — high sigma = noisy, low sigma = clean |

## Complete Code Example: Custom Noise Generator

```python
import torch

class FrequencyNoiseGenerator:
    """Generates noise with adjustable frequency characteristics."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frequency": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.1,
                    "max": 10.0,
                    "step": 0.1,
                    "tooltip": "Frequency of the noise pattern"
                }),
                "exponent": ("FLOAT", {
                    "default": -2.0,
                    "min": -5.0,
                    "max": 5.0,
                    "step": 0.1,
                    "tooltip": "Frequency falloff exponent (negative = low-frequency dominant)"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Random seed"
                }),
            }
        }

    RETURN_TYPES = ("NOISE",)
    RETURN_NAMES = ("noise",)
    FUNCTION = "create_noise"
    CATEGORY = "sampling/noise"

    def create_noise(self, frequency, exponent, seed):
        gen = FrequencyNoise(frequency, exponent, seed)
        return (gen,)


class FrequencyNoise:
    """Noise generator with frequency-domain control."""

    def __init__(self, frequency, exponent, seed):
        self.frequency = frequency
        self.exponent = exponent
        self.seed = seed

    def generate_noise(self, latent, seed_override=None):
        """Generate noise matching the latent tensor shape.

        Args:
            latent: dict containing "samples" key with tensor [B, C, H, W]
            seed_override: optional seed to use instead of self.seed

        Returns:
            Noise tensor matching latent shape
        """
        samples = latent["samples"]
        B, C, H, W = samples.shape
        seed = seed_override if seed_override is not None else self.seed

        # Generate noise in frequency domain
        generator = torch.Generator(device=samples.device)
        generator.manual_seed(seed)

        # Create random noise
        noise = torch.randn(B, C, H, W, generator=generator, device=samples.device, dtype=samples.dtype)

        # Apply frequency shaping via FFT
        # Transform to frequency domain
        freq = torch.fft.fft2(noise)
        freq = torch.fft.fftshift(freq)

        # Create frequency mask
        cy, cx = H // 2, W // 2
        y = torch.arange(H, device=samples.device, dtype=torch.float32) - cy
        x = torch.arange(W, device=samples.device, dtype=torch.float32) - cx
        yy, xx = torch.meshgrid(y, x, indexing="ij")
        dist = torch.sqrt(xx**2 + yy**2) + 1e-8

        # Frequency filter: 1/f^exponent scaled by frequency parameter
        freq_filter = (dist * self.frequency) ** self.exponent
        freq_filter = freq_filter / freq_filter.mean()  # Normalize

        # Apply filter
        freq_filtered = freq * freq_filter.unsqueeze(0).unsqueeze(0)

        # Transform back to spatial domain
        freq_filtered = torch.fft.ifftshift(freq_filtered)
        noise_filtered = torch.fft.ifft2(freq_filtered).real

        # Normalize to unit variance
        noise_filtered = noise_filtered / noise_filtered.std()

        return noise_filtered
```

## Complete Code Example: Custom Sigma Schedule

```python
import torch

class CustomSigmaSchedule:
    """Creates a custom noise schedule (sigmas) for sampling."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 1000}),
                "sigma_max": ("FLOAT", {"default": 14.6146, "min": 0.0, "max": 1000.0, "step": 0.001}),
                "sigma_min": ("FLOAT", {"default": 0.002, "min": 0.0, "max": 100.0, "step": 0.001}),
                "schedule": (["linear", "cosine", "exponential", "sine"],),
                "rho": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 100.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("SIGMAS",)
    RETURN_NAMES = ("sigmas",)
    FUNCTION = "create_sigmas"
    CATEGORY = "sampling/schedules"

    def create_sigmas(self, steps, sigma_max, sigma_min, schedule, rho):
        if schedule == "linear":
            sigmas = torch.linspace(sigma_max, sigma_min, steps + 1)
        elif schedule == "cosine":
            t = torch.linspace(0, 1, steps + 1)
            sigmas = sigma_max * torch.cos(t * torch.pi / 2)
            sigmas = sigmas * (sigma_max - sigma_min) / sigma_max + sigma_min
        elif schedule == "exponential":
            sigmas = torch.logspace(
                torch.log10(torch.tensor(sigma_max)),
                torch.log10(torch.tensor(sigma_min)),
                steps + 1
            )
        elif schedule == "sine":
            t = torch.linspace(0, 1, steps + 1)
            sigmas = sigma_max * torch.sin((1 - t) * torch.pi / 2)
            sigmas = sigmas * (sigma_max - sigma_min) / sigma_max + sigma_min
        else:
            raise ValueError(f"Unknown schedule: {schedule}")

        # Ensure last sigma is 0 (fully denoised)
        sigmas[-1] = 0.0

        return (sigmas,)
```

## SIGMAS Structure

```python
# SIGMAS is a 1D tensor with length = steps + 1
# Example for 5 steps:
sigmas = tensor([14.6146, 9.5, 5.2, 2.1, 0.5, 0.0])
#                        ↑                      ↑
#                   sigma_max              sigma_min (always 0)

# Each consecutive pair defines a denoising step:
# step 0: sigma 14.6146 → 9.5  (heavy denoising)
# step 1: sigma 9.5 → 5.2
# ...
# step 4: sigma 0.5 → 0.0      (final cleanup)
```

## Key Considerations

1. **NOISE.generate_noise() receives a latent dict.** The `"samples"` key contains the tensor `[B, C, H, W]`. Match this shape exactly.

2. **Seed handling.** ComfyUI passes seeds to noise generators. Your `generate_noise` should accept `seed_override` or handle seed from the latent dict's `"noise_seed"` key.

3. **SIGMAS must end with 0.0.** The final sigma value must be 0.0 for the sampler to fully denoise the image. ComfyUI samplers expect this.

4. **Sigma ordering.** Sigmas should be monotonically decreasing from `sigma_max` to `0.0`. Some samplers may break with non-monotonic schedules.

5. **Latent space dimensions.** Latent tensors are typically 4× smaller than pixel space (e.g., 512×512 image → 64×64 latent). Your noise must match latent dimensions.

6. **Device consistency.** Create tensors on the same device as the latent. Use `samples.device` for device inference.

7. **Dtype consistency.** Match the latent's dtype (usually `float32` or `float16`). Use `samples.dtype`.

## Variations

### Image-Based Noise (img2img with noise from image)

```python
class ImageToNoise:
    """Creates noise based on a reference image for img2img workflows."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }

    RETURN_TYPES = ("NOISE",)
    FUNCTION = "create_noise"
    CATEGORY = "sampling/noise"

    def create_noise(self, image, strength, seed):
        gen = ImageNoise(image, strength, seed)
        return (gen,)


class ImageNoise:
    def __init__(self, image, strength, seed):
        self.image = image
        self.strength = strength
        self.seed = seed

    def generate_noise(self, latent, seed_override=None):
        samples = latent["samples"]
        B, C, H, W = samples.shape
        seed = seed_override if seed_override is not None else self.seed

        generator = torch.Generator(device=samples.device)
        generator.manual_seed(seed)

        # Random noise
        noise = torch.randn(B, C, H, W, generator=generator, device=samples.device, dtype=samples.dtype)

        # Blend noise with image features (simplified)
        # In practice, you'd encode the image through VAE first
        image_noise = noise * (1 - self.strength) + torch.randn_like(noise) * self.strength

        return image_noise
```

### Sigma Scheduler with Warmup

```python
class WarmupSigmaSchedule:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 1000}),
                "warmup_steps": ("INT", {"default": 3, "min": 0, "max": 100}),
                "sigma_max": ("FLOAT", {"default": 14.6146, "min": 0.0, "max": 1000.0}),
                "sigma_min": ("FLOAT", {"default": 0.002, "min": 0.0, "max": 100.0}),
            }
        }

    RETURN_TYPES = ("SIGMAS",)
    FUNCTION = "create_sigmas"
    CATEGORY = "sampling/schedules"

    def create_sigmas(self, steps, warmup_steps, sigma_max, sigma_min):
        # Linear schedule
        sigmas = torch.linspace(sigma_max, sigma_min, steps + 1)

        # Warmup: keep high sigma for first N steps
        if warmup_steps > 0:
            sigmas[:warmup_steps] = sigma_max

        sigmas[-1] = 0.0
        return (sigmas,)
```

### Noise Blending

```python
class NoiseBlend:
    """Blends two noise patterns together."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "noise_a": ("NOISE",),
                "noise_b": ("NOISE",),
                "blend": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("NOISE",)
    FUNCTION = "blend_noise"
    CATEGORY = "sampling/noise"

    def blend_noise(self, noise_a, noise_b, blend):
        return (BlendedNoise(noise_a, noise_b, blend),)


class BlendedNoise:
    def __init__(self, noise_a, noise_b, blend):
        self.noise_a = noise_a
        self.noise_b = noise_b
        self.blend = blend

    def generate_noise(self, latent, seed_override=None):
        na = self.noise_a.generate_noise(latent, seed_override)
        nb = self.noise_b.generate_noise(latent, seed_override)
        return na * (1 - self.blend) + nb * self.blend
```
