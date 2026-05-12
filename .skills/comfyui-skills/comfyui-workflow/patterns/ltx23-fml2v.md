# LTX 2.3 First-Middle-Last-Frame to Video (FML2V)

Generate a video guided by three reference images: first frame, middle frame, and last frame.

## When to Use

- Complex scene transitions with a defined midpoint
- Multi-phase animations (e.g., object appearing → fully visible → disappearing)
- Camera movement control with a known midpoint composition
- Character pose sequences with a specific mid-pose
- When FLF2V produces unwanted motion in the middle of the clip

## Required Nodes

| Node | Purpose |
|------|---------|
| `UNETLoader` | Load `ltx-2.3-22b-dev-fp8.safetensors` |
| `DualCLIPLoader` | Load `gemma_3_12B_it_fp8` text encoder |
| `LoadImage` (×3) | Load first, middle, and last frames |
| `ResizeImagesByLongerEdge` | Resize all images to 1536px |
| `LTXVImgToVideoInplaceKJ` | Encode first frame into latent |
| `LTXVConditioning` | Apply conditioning (frame_rate=24) |
| `LTXVAddGuideMulti` | Inject multiple guide frames at different timesteps |
| `LTXVCropGuides` | Crop guides to match latent dimensions |
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
      → LTXVConditioning (frame_rate=24)

LoadImage (middle frame)
  → ResizeImagesByLongerEdge (longer_edge=1536)
    → LTXVCropGuides → LTXVAddGuideMulti (guide_2, sigma≈0.5)

LoadImage (last frame)
  → ResizeImagesByLongerEdge (longer_edge=1536)
    → LTXVCropGuides → LTXVAddGuideMulti (guide_3, sigma≈0.975)

LTXVConditioning
  → LTXVAddGuideMulti (conditioning input)
    → CFGGuider
      → SamplerCustomAdvanced
        → LTXVSeparateAVLatent
          → LTXVSpatioTemporalTiledVAEDecode
            → VHS_VideoCombine
```

## Key Considerations

- **Three images**: First frame is encoded directly; middle and last are injected as guides
- **Middle frame timing**: Injected at ~50% timestep (sigma≈0.5) to control the midpoint composition
- **Last frame timing**: Injected at ~97.5% timestep (sigma≈0.975) same as FLF2V
- **Guide conflicts**: If middle and last frames are too different, the model may struggle to reconcile them
- **Resolution consistency**: All three images must be resized identically
- **Motion complexity**: More guides = more constrained motion; may reduce naturalness
- **Frame count**: Use 97–161 frames for best results; 201 may spread guides too thin
- **Strength balance**: Middle frame typically needs lower strength than last frame

## Sigma / Config Examples

### 9-Step Sigmas (shared with FLF2V)

```
1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0
```

### Guide Injection Config

| Guide | Sigma | Strength | Notes |
|-------|-------|----------|-------|
| First frame | N/A (encoded) | 1.0 | Directly encoded into latent |
| Middle frame | 0.5 | 0.6–0.8 | Controls midpoint composition |
| Last frame | 0.975 | 0.8–1.0 | Controls final frame |

### LTXVAddGuideMulti Widget Values

```
guide_2_sigma: 0.5       # Middle frame injection point
guide_2_strength: 0.7    # Middle frame influence
guide_3_sigma: 0.975     # Last frame injection point
guide_3_strength: 1.0    # Last frame influence
```

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
| Frames | 97 (4s) / 161 (6.7s) |

### Middle Frame Placement by Frame Count

| Total Frames | Middle Frame Index | Middle Sigma |
|--------------|-------------------|--------------|
| 97 | 48–49 | 0.5 |
| 121 | 60 | 0.5 |
| 161 | 80 | 0.5 |
| 201 | 100 | 0.5 |
