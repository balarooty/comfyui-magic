# LTX 2.3 First-Last-Frame to Video (FLF2V)

Generate a video that transitions between two reference images: a first frame and a last frame.

## When to Use

- Creating smooth transitions between two distinct images
- Scene morphing (e.g., day→night, person→person, style transfer over time)
- Storyboarding where start and end states are defined
- Product demos showing before/after states
- When you need deterministic start and end points for the animation

## Required Nodes

| Node | Purpose |
|------|---------|
| `UNETLoader` | Load `ltx-2.3-22b-dev-fp8.safetensors` |
| `DualCLIPLoader` | Load `gemma_3_12B_it_fp8` text encoder |
| `LoadImage` (×2) | Load first frame + last frame |
| `ResizeImagesByLongerEdge` | Resize both images to 1536px |
| `LTXVImgToVideoInplaceKJ` | Encode first frame into latent |
| `LTXVConditioning` | Apply conditioning (frame_rate=24) |
| `LTXVAddGuide` | Inject last frame guidance at specific timestep |
| `LTXVCropGuides` | Manage guide cropping for consistency |
| `CFGGuider` | Configure guidance |
| `SamplerCustomAdvanced` | Run the sampler |
| `LTXVSeparateAVLatent` | Separate audio/video latents |
| `LTXVSpatioTemporalTiledVAEDecode` | Decode output |
| `VHS_VideoCombine` | Output video |

## Connection Order

```
LoadImage (first frame)
  → ResizeImagesByLongerEdge (longer_edge=1536)
    → LTXVImgToVideoInplaceKJ (encode as starting frame)
      → LTXVConditioning (frame_rate=24, strength=1.0)

LoadImage (last frame)
  → ResizeImagesByLongerEdge (longer_edge=1536)
    → LTXVCropGuides (crop to match latent dimensions)
      → LTXVAddGuide (inject at late timestep, e.g., 0.975)
        → CFGGuider (guide input)

LTXVConditioning
  → CFGGuider
    → SamplerCustomAdvanced
      → LTXVSeparateAVLatent
        → LTXVSpatioTemporalTiledVAEDecode
          → VHS_VideoCombine

[Latent source]
EmptyLTXVLatentVideo → LTXVImgToVideoInplaceKJ → SamplerCustomAdvanced
```

## Key Considerations

- **Two images required**: First frame drives the start; last frame drives the end
- **Guide timestep**: The last frame is injected near the end of the denoising process (e.g., sigma=0.975) to influence the final frame without overriding the motion trajectory
- **Resolution consistency**: Both images must be resized to the same dimensions; `ResizeImagesByLongerEdge` ensures this
- **Crop alignment**: `LTXVCropGuides` ensures the guide image matches the latent spatial dimensions
- **Motion quality**: The transition quality depends on how different the two frames are; very different images may produce artifacts
- **Longer sigmas**: 9-step schedule provides more control points than the distilled 4-step
- **Strength tuning**: `LTXVAddGuide` strength controls how strongly the last frame influences the output

## Sigma / Config Examples

### 9-Step Sigmas for FLF2V

```
1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0
```

### Guide Injection Config

| Parameter | Value | Notes |
|-----------|-------|-------|
| Guide sigma | 0.975 | Inject last frame at this timestep |
| Guide strength | 0.8–1.0 | How strongly last frame influences output |
| Guide type | `last_frame` | Position of the guided frame |

### Resolution Config

| Setting | Value |
|---------|-------|
| Resize longer edge | 1536 px |
| Maintain aspect ratio | Yes |
| Output resolution | 1280×720 or 1920×1080 |

### Sampler Config

| Parameter | Value |
|-----------|-------|
| Sampler | `euler_ancestral_cfg_pp` |
| Scheduler | `sgm_uniform` |
| Steps | 9 |
| CFG | 1 (distilled) / 4 (base) |
| Frame rate | 24 fps |
| Frames | 97–201 |

### LTXVAddGuide Widget Values

```
sigma: 0.975          # When to inject the guide
strength: 1.0         # Influence strength
guide_type: "last"    # Position in sequence
```

### LTXVCropGuides Config

```
width: <latent_width>   # e.g., 320 for 1280px
height: <latent_height> # e.g., 180 for 720px
```
