# LTX 2.3 Video-to-Video (V2V)

Transform an existing video by re-sampling it with partial denoise, preserving temporal structure while altering content.

## When to Use

- Style transfer on existing footage (e.g., realistic → anime, day → night)
- Subtle enhancement or correction of generated videos
- Modifying specific attributes (color, texture, lighting) while keeping motion
- Iterative refinement: generate → identify issues → fix with V2V
- Applying consistent edits across all frames of a video

## Required Nodes

| Node | Purpose |
|------|---------|
| `UNETLoader` | Load `ltx-2.3-22b-dev-fp8.safetensors` |
| `DualCLIPLoader` | Load `gemma_3_12B_it_fp8` text encoder |
| `VHS_LoadVideo` | Load source video |
| `VAEEncode` | Encode video frames to latent space |
| `CLIPTextEncode` | Encode transformation prompt |
| `LTXVConditioning` | Apply conditioning |
| `CFGGuider` | Configure guidance with partial denoise |
| `SamplerCustomAdvanced` | Re-sample with reduced steps |
| `LTXVSpatioTemporalTiledVAEDecode` | Decode latent to pixels |
| `VHS_VideoCombine` | Output transformed video |

## Connection Order

```
VHS_LoadVideo (source video)
  → VAEEncode (encode to latent)
    → SamplerCustomAdvanced (latent input, denoise < 1.0)

CLIPTextEncode (transformation prompt)
  → LTXVConditioning (frame_rate=24)
    → CFGGuider
      → SamplerCustomAdvanced

SamplerCustomAdvanced
  → LTXVSpatioTemporalTiledVAEDecode
    → VHS_VideoCombine
```

## Key Considerations

- **Denoise strength** is the key parameter:
  - `0.2–0.3`: Minor changes (color grading, subtle style shift)
  - `0.4–0.5`: Moderate changes (texture, lighting, mild style transfer)
  - `0.6–0.7`: Major changes (strong style transfer, significant content alteration)
  - `0.8–1.0`: Near-complete regeneration (loses most source structure)
- **Source video quality**: Garbage in, garbage out; start with clean source footage
- **Frame alignment**: Source video frame count should match the target frame count
- **Resolution matching**: Encode at the same resolution you want to decode at
- **Temporal consistency**: Lower denoise preserves more temporal coherence
- **Prompt specificity**: Be specific about what to change; vague prompts cause unpredictable results
- **Audio**: Audio from source video is not preserved; regenerate if needed

## Sigma / Config Examples

### Denoise-to-Sigma Mapping

For partial denoise, sigmas start from the denoise value instead of 1.0:

| Denoise | Start Sigma | Effective Steps (of 50) |
|---------|-------------|------------------------|
| 0.2 | 0.2 | 10 |
| 0.3 | 0.3 | 15 |
| 0.5 | 0.5 | 25 |
| 0.7 | 0.7 | 35 |
| 1.0 | 1.0 | 50 |

### Distilled 4-Step with Denoise 0.5

```
0.425, 0.3625, 0.2109, 0.0
```

(Scaled: sigma × denoise for each step)

### Full 50-Step at Denoise 0.3

```
0.3, 0.294, 0.288, 0.282, 0.276, 0.27, 0.261, 0.252, 0.24, 0.228,
0.216, 0.204, 0.192, 0.18, 0.168, 0.156, 0.144, 0.132, 0.12, 0.108,
0.096, 0.084, 0.072, 0.06, 0.048, 0.036, 0.024, 0.012, 0.0
```

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
| Denoise | 0.3–0.7 (typical range) |
| Frame rate | 24 fps |

### VHS_LoadVideo Config

```
video: <path_to_source_video>
force_rate: 24          # Match target frame rate
force_size: 1280×720    # Match target resolution
custom_width: 1280
custom_height: 720
```

### Recommended Denoise by Use Case

| Use Case | Denoise | Prompt Style |
|----------|---------|--------------|
| Color grading | 0.2 | "warm cinematic tones" |
| Lighting change | 0.3 | "dramatic sunset lighting" |
| Style transfer | 0.5 | "in the style of oil painting" |
| Heavy stylization | 0.7 | "cyberpunk neon aesthetic" |
| Near-regeneration | 0.9 | Full descriptive prompt |
