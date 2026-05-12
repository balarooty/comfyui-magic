# LTX 2.3 Text-to-Video (T2V)

Generate a video purely from a text prompt using the LTX 2.3 pipeline.

## When to Use

- Creating videos from scratch with no reference image
- Conceptual or abstract motion generation
- When text description is sufficient for the desired output
- Quick iteration on ideas before committing to I2V refinement

## Required Nodes

| Node | Purpose |
|------|---------|
| `UNETLoader` | Load `ltx-2.3-22b-dev-fp8.safetensors` |
| `DualCLIPLoader` | Load `gemma_3_12B_it_fp8` text encoder |
| `EmptyLTXVLatentVideo` | Create empty latent (480×256, 97 frames) |
| `CLIPTextEncode` | Encode text prompt (positive + negative) |
| `LTXVConditioning` | Apply conditioning (frame_rate=24) |
| `CFGGuider` | Configure guidance |
| `SamplerCustomAdvanced` | Run the sampler |
| `LTXVSeparateAVLatent` | Separate audio/video latents |
| `LTXVSpatioTemporalTiledVAEDecode` | Decode latent to pixels |
| `VHS_VideoCombine` | Output video |

## Connection Order

```
CLIPTextEncode (positive prompt)
  → LTXVConditioning (frame_rate=24)
    → CFGGuider (cfg=1 distilled / cfg=4 base)
      → SamplerCustomAdvanced
        → LTXVSeparateAVLatent
          → LTXVSpatioTemporalTiledVAEDecode
            → VHS_VideoCombine

[Latent source]
EmptyLTXVLatentVideo (width=480, height=256, length=97)
  → SamplerCustomAdvanced (latent input)

[Guider source]
BasicScheduler (sigmas) → SamplerCustomAdvanced
UniformNoiseGenerator → SamplerCustomAdvanced
```

## Key Considerations

- **No reference image**: The entire video is generated from text alone
- **Latent resolution**: Default 480×256 corresponds to ~1920×1024 pixels
- **Prompt engineering matters more** in T2V since there's no visual anchor
- **Negative prompts**: Use to avoid common artifacts (blurry, distorted, static)
- **Latent upsampling**: Optionally apply LTX latent upsampler for higher resolution
- **Frame count**: 97 frames is the sweet spot; longer clips may lose coherence
- **Audio generation**: Same audio path as I2V if enabled

## Sigma / Config Examples

### Distilled 4-Step Sigmas

```
0.85, 0.7250, 0.4219, 0.0
```

### Empty Latent Config

| Parameter | Value |
|-----------|-------|
| Width | 480 |
| Height | 256 |
| Length | 97 |
| Batch size | 1 |

### CFG Values

| Mode | CFG |
|------|-----|
| Distilled | 1.0 |
| Base | 4.0 |

### Sampler Config

| Parameter | Value |
|-----------|-------|
| Sampler | `euler_ancestral_cfg_pp` |
| Scheduler | `sgm_uniform` |
| Steps | 4 (distilled) / 50 (base) |
| Frame rate | 24 fps |

### Prompt Template

```
Positive: "A [subject] [action] in [setting], cinematic lighting, smooth motion"
Negative: "blurry, distorted, static, low quality, watermark"
```

### Optional Latent Upsampling

After initial generation at 480×256, apply:
1. `LTXVLatentUpsampler` to scale latent 2×
2. Re-sample at higher resolution with reduced denoise (0.5–0.7)
3. Decode final latent
