# Latent Upsampling Pattern

## When to Use

Generate video or images at low resolution, then upscale in latent space without decoding to pixels. Use when you need high-resolution output but want to save VRAM during initial generation. The two-pass approach (base + refinement) produces cleaner results than single-pass high-res generation.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Load base diffusion model |
| `EmptyLatentImage` or `EmptyLTXVLatentVideo` | Create low-res latent |
| `KSampler` | Base sampling at low resolution |
| `LatentUpscaleModelLoader` | Load spatial upscaler model |
| `LTXVLatentUpsampler` | Upscale latent by 2x |
| `KSampler` (second) | Refinement pass at higher resolution |
| `VAEDecode` | Decode final latent to pixels |
| `SaveImage` or `SaveVideo` | Save output |

## Connection Order

```
CheckpointLoaderSimple
  ├── MODEL → KSampler_base.model
  ├── MODEL → KSampler_refine.model
  ├── CLIP  → CLIPTextEncode.clip
  └── VAE   → VAEDecode.vae

EmptyLatentImage (low res)
  └── LATENT → KSampler_base.latent_image

KSampler_base
  └── LATENT → LTXVLatentUpsampler.samples

LatentUpscaleModelLoader
  └── UPSCALE_MODEL → LTXVLatentUpsampler.upscale_model

LTXVLatentUpsampler
  └── LATENT → KSampler_refine.latent_image

KSampler_refine (low denoise)
  └── LATENT → VAEDecode.samples

VAEDecode
  └── IMAGE → SaveImage.images
```

## Node-by-Node Wiring Guide

### 1. EmptyLatentImage (Low Resolution)

```
Inputs:
  width:      480                                  (widget, int)
  height:     256                                  (widget, int)
  batch_size: 1                                    (widget, int)

Outputs:
  LATENT → KSampler_base.latent_image
```

### 2. KSampler_base

```
Inputs:
  model:        ← CheckpointLoaderSimple.MODEL
  positive:     ← CLIPTextEncode.positive
  negative:     ← CLIPTextEncode.negative
  latent_image: ← EmptyLatentImage.LATENT
  seed:         42                                 (widget, int)
  steps:        30                                 (widget, int)
  cfg:          7.0                                (widget, float)
  sampler_name: "dpmpp_2m"                         (widget, enum)
  scheduler:    "karras"                           (widget, enum)

Outputs:
  LATENT → LTXVLatentUpsampler.samples
```

### 3. LatentUpscaleModelLoader

```
Inputs:
  model_name: "latent_upscaler_x2.safetensors"    (widget, model file)

Outputs:
  UPSCALE_MODEL → LTXVLatentUpsampler.upscale_model
```

### 4. LTXVLatentUpsampler

```
Inputs:
  samples:        ← KSampler_base.LATENT
  upscale_model:  ← LatentUpscaleModelLoader.UPSCALE_MODEL
  scale_factor:   2.0                              (widget, float)

Outputs:
  LATENT → KSampler_refine.latent_image
```

### 5. KSampler_refine

```
Inputs:
  model:        ← CheckpointLoaderSimple.MODEL
  positive:     ← CLIPTextEncode.positive (same prompt)
  negative:     ← CLIPTextEncode.negative (same prompt)
  latent_image: ← LTXVLatentUpsampler.LATENT
  seed:         42                                 (widget, int — same seed)
  steps:        15                                 (widget, int — fewer steps)
  cfg:          5.0                                (widget, float — lower cfg)
  sampler_name: "dpmpp_2m"                         (widget, enum)
  scheduler:    "karras"                           (widget, enum)
  denoise:      0.2                                (widget, float — LOW denoise)

Outputs:
  LATENT → VAEDecode.samples
```

### 6. VAEDecode

```
Inputs:
  samples: ← KSampler_refine.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → SaveImage.images
```

## Two-Pass Sampling Strategy

### Base Pass

- Full resolution generation at low res (480×256 for video, 512×512 for images)
- Full step count (25-40 steps)
- Standard CFG (5-8)
- Establishes composition, layout, and global structure

### Refinement Pass

- Operates on upscaled latent (960×512 for video, 1024×1024 for images)
- Reduced step count (10-20 steps)
- Lower CFG (3-5)
- Low denoise strength (0.1-0.3) — preserves base composition
- Adds fine detail and sharpness at higher resolution

## Key Considerations

- **Denoise strength**: The refinement pass must use low denoise (0.1-0.3). High denoise destroys the base composition and produces artifacts.
- **Same seed**: Use the same seed for both passes to maintain consistency. Different seeds cause the refinement to diverge from the base.
- **Same prompt**: Both passes should use identical prompts. Different prompts cause semantic drift.
- **Upscale model compatibility**: The latent upscaler must match the base model's latent channel count. SDXL latents (4 channels) need an SDXL-compatible upscaler.
- **VRAM savings**: Generating at 480×256 then upscaling uses ~60% less VRAM than direct 960×512 generation.
- **Quality tradeoff**: Two-pass is not always better than single-pass at target resolution. For simple scenes, direct generation may suffice.
- **Multiple upscale passes**: You can chain multiple 2x upscales (256→512→1024) but quality degrades with each pass. Two passes is the practical limit.
- **Video temporal coherence**: For video, the upsampler preserves temporal coherence across frames. The refinement pass should not use temporal-aware samplers that conflict with the upsampler.
- **CFG decay**: Reduce CFG in refinement (e.g., 7.0 → 5.0) to avoid over-sharpening and artifacts at higher resolution.

## Example Widget Values

### Standard Two-Pass Image

```
EmptyLatentImage: width=512, height=512
KSampler_base: seed=42, steps=30, cfg=7.0, sampler_name="dpmpp_2m", scheduler="karras"
LatentUpscaleModelLoader: model_name="latent_upscaler_x2.safetensors"
LTXVLatentUpsampler: scale_factor=2.0
KSampler_refine: seed=42, steps=15, cfg=5.0, denoise=0.2
```

### Video Two-Pass

```
EmptyLTXVLatentVideo: width=480, height=256, frame_count=97
KSampler_base: seed=42, steps=30, cfg=7.0
LTXVLatentUpsampler: scale_factor=2.0
KSampler_refine: seed=42, steps=12, cfg=4.0, denoise=0.15
```

### Three-Pass (Advanced)

```
Base: 256×144, steps=30, cfg=7.0
Upsample 2x → 512×288, refine steps=15, cfg=5.0, denoise=0.25
Upsample 2x → 1024×576, refine steps=10, cfg=3.5, denoise=0.15
```
