# LTX 2.3 Text + Image to Video (TI2V)

Dual-mode pipeline that switches between Image-to-Video and Text-to-Video using a boolean toggle.

## When to Use

- Building a flexible workflow that supports both I2V and T2V modes
- A/B testing image-guided vs. text-only generation
- When you want optional image input without maintaining two workflows
- Interactive ComfyUI setups where users toggle modes via a switch

## Required Nodes

| Node | Purpose |
|------|---------|
| `UNETLoader` | Load `ltx-2.3-22b-dev-fp8.safetensors` |
| `DualCLIPLoader` | Load `gemma_3_12B_it_fp8` text encoder |
| `LoadImage` | Load reference image (optional, bypassed in T2V mode) |
| `PrimitiveBoolean` | `Switch_to_T2V` toggle |
| `LTXVImgToVideoConditionOnly` | Condition on image (bypassed when T2V) |
| `CLIPTextEncode` | Encode text prompt |
| `LTXVConditioning` | Apply conditioning |
| `EmptyLTXVLatentVideo` | Create empty latent |
| `CFGGuider` | Configure guidance |
| `SamplerCustomAdvanced` | Run the sampler |
| `LTXVSeparateAVLatent` | Separate audio/video latents |
| `LTXVSpatioTemporalTiledVAEDecode` | Decode output |
| `VHS_VideoCombine` | Output video |

## Connection Order

```
PrimitiveBoolean (Switch_to_T2V)
  → LTXVImgToVideoConditionOnly.bypass (True = bypass = T2V mode)

LoadImage
  → LTXVImgToVideoConditionOnly (encode reference when not bypassed)
    → LTXVConditioning (frame_rate=24)
      → CFGGuider
        → SamplerCustomAdvanced
          → LTXVSeparateAVLatent
            → LTXVSpatioTemporalTiledVAEDecode
              → VHS_VideoCombine

CLIPTextEncode (prompt)
  → LTXVConditioning (text conditioning)

EmptyLTXVLatentVideo
  → SamplerCustomAdvanced (latent input)
```

## Key Considerations

- **Resolution math**: Latent dimensions = pixel dimensions × 0.25
  - 1280×720 → latent 320×180
  - 1920×1080 → latent 480×270
- **Bypass behavior**: When `Switch_to_T2V` is True, `LTXVImgToVideoConditionOnly` is bypassed and the image input is ignored
- **Conditioning merge**: In I2V mode, both image and text conditioning are applied; in T2V mode, only text conditioning
- **Frame dimensions**: Must be divisible by 16 for the VAE; use `ResizeImageMaskNode` to ensure compliance
- **Batch size**: Keep at 1 for consistency across the latent and conditioning paths

## Sigma / Config Examples

### Distilled 4-Step Sigmas

```
0.85, 0.7250, 0.4219, 0.0
```

### Resolution ↔ Latent Mapping

| Pixel Width | Pixel Height | Latent Width | Latent Height |
|-------------|--------------|--------------|---------------|
| 1280 | 720 | 320 | 180 |
| 1920 | 1080 | 480 | 270 |
| 1536 | 864 | 384 | 216 |
| 1024 | 576 | 256 | 144 |

### Mode Toggle Config

| Switch_to_T2V | Mode | Image Input | Conditioning |
|---------------|------|-------------|--------------|
| `False` | I2V | Active | Image + Text |
| `True` | T2V | Ignored | Text only |

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
| Frames | 97 |

### PrimitiveBoolean Setup

```
Node: PrimitiveBoolean
  widget_value: False  (default = I2V mode)
  output → LTXVImgToVideoConditionOnly.bypass
```
