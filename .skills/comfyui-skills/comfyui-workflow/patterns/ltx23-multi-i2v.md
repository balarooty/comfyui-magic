# LTX 2.3 Multiple Reference Images to Video (Multi-I2V)

Generate a video guided by multiple reference images using IC-LoRA (Image Conditioning LoRA) for multi-scene transitions.

## When to Use

- Multi-scene narratives with distinct visual anchors
- Transition sequences between multiple products or characters
- Visual storytelling with defined keyframes
- Scene blending where multiple reference images guide different segments
- Marketing videos showing multiple views of a product

## Required Nodes

| Node | Purpose |
|------|---------|
| `UNETLoader` | Load `ltx-2.3-22b-dev-fp8.safetensors` |
| `DualCLIPLoader` | Load `gemma_3_12B_it_fp8` text encoder |
| `LoadImage` (×N) | Load multiple reference images |
| `ResizeImageMaskNode` | Resize each image to target resolution |
| `LTXVImgToVideoInplaceKJ` | Encode primary reference image |
| `LTXVConditioning` | Apply conditioning (frame_rate=24) |
| `LTXAddVideoICLoRAGuide` | Inject each reference image as IC-LoRA guide |
| `CFGGuider` | Configure guidance |
| `SamplerCustomAdvanced` | Run the sampler |
| `LTXVSeparateAVLatent` | Separate audio/video latents |
| `LTXVSpatioTemporalTiledVAEDecode` | Decode output |
| `VHS_VideoCombine` | Output video |

## Connection Order

```
LoadImage (reference_1 / primary)
  → ResizeImageMaskNode (1536px)
    → LTXVImgToVideoInplaceKJ (encode as starting frame)
      → LTXVConditioning (frame_rate=24)

LoadImage (reference_2)
  → ResizeImageMaskNode (1536px)
    → LTXAddVideoICLoRAGuide (guide_1, strength=0.8, timestep=0.5)

LoadImage (reference_3)
  → ResizeImageMaskNode (1536px)
    → LTXAddVideoICLoRAGuide (guide_2, strength=0.6, timestep=0.75)

LTXVConditioning
  → LTXAddVideoICLoRAGuide (×N, chained)
    → CFGGuider
      → SamplerCustomAdvanced
        → LTXVSeparateAVLatent
          → LTXVSpatioTemporalTiledVAEDecode
            → VHS_VideoCombine
```

## Key Considerations

- **IC-LoRA mechanism**: Uses latent-space image conditioning rather than direct pixel injection
- **latent_downscale_factor**: Set to `0.25` — guides are processed at 1/4 latent resolution
- **Primary image**: The first image is encoded directly via `LTXVImgToVideoInplaceKJ`; additional images are IC-LoRA guides
- **Strength per guide**: Each guide has independent strength controlling its influence
- **Timestep per guide**: Each guide is injected at a specific timestep to control when it influences the generation
- **Guide ordering**: Earlier timesteps influence earlier parts of the video; later timesteps influence later parts
- **Diminishing returns**: More than 3–4 guides may cause blending artifacts or incoherent motion
- **Resolution consistency**: All images must be the same resolution

## Sigma / Config Examples

### Distilled 4-Step Sigmas

```
0.85, 0.7250, 0.4219, 0.0
```

### IC-LoRA Guide Config

| Guide | Timestep | Strength | Purpose |
|-------|----------|----------|---------|
| Primary (encoded) | N/A | 1.0 | Starting frame, directly encoded |
| Guide 1 | 0.5 | 0.8 | Mid-video scene anchor |
| Guide 2 | 0.75 | 0.6 | Late-video scene anchor |
| Guide 3 | 0.25 | 0.5 | Early-video detail injection |

### latent_downscale_factor

```
latent_downscale_factor: 0.25
```

This scales guide images to 1/4 of the latent resolution before IC-LoRA injection. For a 1280×720 output (latent 320×180), guides are processed at 80×45.

### LTXAddVideoICLoRAGuide Widget Values

```
guide_1:
  strength: 0.8
  timestep: 0.5
  image: <reference_image_2>

guide_2:
  strength: 0.6
  timestep: 0.75
  image: <reference_image_3>
```

### Multi-Guide Strength Patterns

| Pattern | Guide 1 | Guide 2 | Guide 3 |
|---------|---------|---------|---------|
| Equal influence | 0.7 | 0.7 | 0.7 |
| Primary dominant | 0.9 | 0.5 | 0.5 |
| Transition focus | 0.3 | 0.9 | 0.3 |
| End-heavy | 0.3 | 0.5 | 0.9 |

### Sampler Config

| Parameter | Value |
|-----------|-------|
| Sampler | `euler_ancestral_cfg_pp` |
| Scheduler | `sgm_uniform` |
| Steps | 4 (distilled) / 50 (base) |
| CFG | 1 (distilled) / 4 (base) |
| Frame rate | 24 fps |
| Frames | 97–201 |

### Resolution Config

| Setting | Value |
|---------|-------|
| Resize longer edge | 1536 px |
| Output resolution | 1280×720 or 1920×1080 |
| Latent resolution | 320×180 or 480×270 |
| IC-LoRA guide resolution | 80×45 or 120×68 |
