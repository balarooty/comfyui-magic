# LTX 2.3 Image-to-Video (I2V)

Generate a video from a reference image using the LTX 2.3 distilled pipeline.

## When to Use

- Animating a still image into a video clip
- Product shots, character art, or scene photos that need motion
- Quick prototyping with the distilled 4-step sampler
- When you have a specific starting frame and want controlled motion

## Required Nodes

| Node | Purpose |
|------|---------|
| `UNETLoader` | Load `ltx-2.3-22b-dev-fp8.safetensors` |
| `DualCLIPLoader` | Load `gemma_3_12B_it_fp8` text encoder |
| `LTXLoader` or `LTXModelConfigurator` | Configure LTX model settings |
| `LoadImage` | Load the reference image |
| `ResizeImageMaskNode` | Resize to target resolution (1536px) |
| `LTXVPreprocess` | Preprocess image (img_compression=18) |
| `LTXVImgToVideoInplace` | Encode reference image into latent |
| `LTXVConditioning` | Apply conditioning (frame_rate=24) |
| `CFGGuider` | Configure guidance (cfg=1 for distilled) |
| `SamplerCustomAdvanced` | Run the sampler |
| `LTXVSeparateAVLatent` | Separate audio/video latents |
| `LTXVSpatioTemporalTiledVAEDecode` | Decode latent to pixels (tile: 4×4×16) |
| `VHS_VideoCombine` | Combine frames into video output |

### Optional Audio Nodes

| Node | Purpose |
|------|---------|
| `LTXVAudioVAELoader` | Load audio VAE |
| `LTXVEmptyLatentAudio` | Create empty audio latent |
| `LTXVConcatAVLatent` | Concatenate audio + video latents |
| `LTXVAudioVAEDecode` | Decode audio latent |

## Connection Order

```
LoadImage
  → ResizeImageMaskNode (longer_edge=1536)
    → LTXVPreprocess (img_compression=18)
      → LTXVImgToVideoInplace (encode reference frame)
        → LTXVConditioning (frame_rate=24, strength=1.0)
          → CFGGuider (cfg=1)
            → SamplerCustomAdvanced
              → LTXVSeparateAVLatent
                → LTXVSpatioTemporalTiledVAEDecode
                  → VHS_VideoCombine

[Parallel latent path]
  EmptyLTXVLatentVideo
    → LTXVImgToVideoInplace (latent input)
```

## Key Considerations

- **Distilled model** uses 4 steps with cfg=1; base model needs ~50 steps with cfg=4
- **Resolution**: Use 1280×720 (16:9) or 1920×1080; avoid non-standard ratios
- **Frame count**: 97 frames (~4s at 24fps), up to 201 frames (~8.4s) for longer clips
- **Image compression**: `img_compression=18` balances quality vs. motion fidelity
- **Tiled VAE decode**: Tile size 4×4×16 prevents OOM on large resolutions
- **Distilled LoRA**: Apply `ltx-2.3-22b-distilled-lora` at 0.6 strength for speed
- **Detailer LoRA**: Optional detail LoRA at 1.0 strength for sharper output
- **Audio path**: If generating audio, use `LTXVConcatAVLatent` before sampling

## Sigma / Config Examples

### Distilled 4-Step Sigmas

```
0.85, 0.7250, 0.4219, 0.0
```

### Base Model ~50-Step Sigmas (approximate)

```
1.0, 0.98, 0.96, 0.94, 0.92, 0.90, 0.87, 0.84, 0.80, 0.76,
0.72, 0.68, 0.64, 0.60, 0.56, 0.52, 0.48, 0.44, 0.40, 0.36,
0.32, 0.28, 0.24, 0.20, 0.16, 0.12, 0.08, 0.04, 0.0
```

### CFG Values

| Mode | CFG |
|------|-----|
| Distilled | 1.0 |
| Base | 4.0 |
| Creative (base) | 6.0–8.0 |

### Sampler Config

| Parameter | Value |
|-----------|-------|
| Sampler | `euler_ancestral_cfg_pp` |
| Scheduler | `sgm_uniform` |
| Steps | 4 (distilled) / 50 (base) |
| Frame rate | 24 fps |
| Frames | 97 (4s) / 161 (6.7s) / 201 (8.4s) |

### Resolution Presets

| Preset | Width | Height | Latent W | Latent H |
|--------|-------|--------|----------|----------|
| 720p | 1280 | 720 | 320 | 180 |
| 1080p | 1920 | 1080 | 480 | 270 |
