# Audio-Video Fusion Pattern

## When to Use

Generate video with synchronized audio in a single workflow. Use when you need to combine video and audio latents into a unified latent space before sampling, then separate them after decoding. Essential for any LTXV audio-video generation task where temporal alignment between sound and visuals matters.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `LTXVModelLoader` or `CheckpointLoaderSimple` | Load the LTXV video model |
| `LTXVAudioVAELoader` | Load the audio VAE model (separate from video VAE) |
| `EmptyLatentImage` or `EmptyLTXVLatentVideo` | Create blank video latent |
| `EmptyLTXVAudioLatent` | Create blank audio latent |
| `LTXVConcatAVLatent` | Combine video + audio latents into single latent |
| `KSampler` | Denoise the fused latent |
| `LTXVSeparateAVLatent` | Split sampled latent back into video and audio |
| `VAEDecode` | Decode video latent to frames |
| `LTXVAudioVAEDecode` | Decode audio latent to waveform |
| `LTXVAudioVAEEncode` | Encode audio input to latent (optional, for audio conditioning) |
| `SaveVideo` | Save output video |
| `SaveAudio` | Save output audio |

## Connection Order

```
LTXVModelLoader
  ├── MODEL → KSampler.model
  └── VAE   → VAEDecode.vae

LTXVAudioVAELoader
  └── AUDIO_VAE → LTXVAudioVAEDecode.audio_vae
                → LTXVAudioVAEEncode.audio_vae

EmptyLTXVLatentVideo
  └── LATENT → LTXVConcatAVLatent.video_latent

EmptyLTXVAudioLatent
  └── LATENT → LTXVConcatAVLatent.audio_latent

LTXVConcatAVLatent
  └── LATENT → KSampler.latent_image

KSampler (denoise fused latent)
  └── LATENT → LTXVSeparateAVLatent.samples

LTXVSeparateAVLatent
  ├── VIDEO_LATENT → VAEDecode.samples
  └── AUDIO_LATENT → LTXVAudioVAEDecode.samples

VAEDecode
  └── IMAGE → SaveVideo.images

LTXVAudioVAEDecode
  └── AUDIO → SaveAudio.audio
```

## Node-by-Node Wiring Guide

### 1. LTXVModelLoader

```
Inputs:
  model_name: "ltxv-13b.safetensors"               (widget, model file)

Outputs:
  MODEL → KSampler.model
  VAE   → VAEDecode.vae
```

### 2. LTXVAudioVAELoader

```
Inputs:
  audio_vae_name: "ltxv_audio_vae.safetensors"      (widget, model file)

Outputs:
  AUDIO_VAE → LTXVAudioVAEDecode.audio_vae
            → LTXVAudioVAEEncode.audio_vae
```

### 3. EmptyLTXVLatentVideo

```
Inputs:
  width:       480                                  (widget, int)
  height:      256                                  (widget, int)
  frame_count: 97                                   (widget, int)
  batch_size:  1                                    (widget, int)

Outputs:
  LATENT → LTXVConcatAVLatent.video_latent
```

### 4. EmptyLTXVAudioLatent

```
Inputs:
  frame_count: 97                                   (widget, int — MUST match video)
  sample_rate: 24000                                (widget, int)

Outputs:
  LATENT → LTXVConcatAVLatent.audio_latent
```

### 5. LTXVConcatAVLatent

```
Inputs:
  video_latent: ← EmptyLTXVLatentVideo.LATENT
  audio_latent: ← EmptyLTXVAudioLatent.LATENT
  fps:          24.0                                (widget, float)

Outputs:
  LATENT → KSampler.latent_image
```

### 6. KSampler

```
Inputs:
  model:        ← LTXVModelLoader.MODEL
  positive:     ← CLIPTextEncode.positive
  negative:     ← CLIPTextEncode.negative
  latent_image: ← LTXVConcatAVLatent.LATENT
  seed:         42                                  (widget, int)
  steps:        30                                  (widget, int)
  cfg:          7.0                                 (widget, float)
  sampler_name: "dpmpp_2m"                          (widget, enum)
  scheduler:    "karras"                            (widget, enum)

Outputs:
  LATENT → LTXVSeparateAVLatent.samples
```

### 7. LTXVSeparateAVLatent

```
Inputs:
  samples: ← KSampler.LATENT

Outputs:
  VIDEO_LATENT → VAEDecode.samples
  AUDIO_LATENT → LTXVAudioVAEDecode.samples
```

### 8. VAEDecode (Video)

```
Inputs:
  samples: ← LTXVSeparateAVLatent.VIDEO_LATENT
  vae:     ← LTXVModelLoader.VAE

Outputs:
  IMAGE → SaveVideo.images
```

### 9. LTXVAudioVAEDecode

```
Inputs:
  samples:   ← LTXVSeparateAVLatent.AUDIO_LATENT
  audio_vae: ← LTXVAudioVAELoader.AUDIO_VAE

Outputs:
  AUDIO → SaveAudio.audio
```

### 10. LTXVAudioVAEEncode (Optional — for audio conditioning)

```
Inputs:
  audio:     ← LoadAudio.audio
  audio_vae: ← LTXVAudioVAELoader.AUDIO_VAE
  frame_count: 97                                   (widget, int)

Outputs:
  LATENT → (use as conditioning input)
```

## Key Considerations

- **Frame rate alignment**: The `fps` parameter in `LTXVConcatAVLatent` must match the frame rate used during video latent creation. Mismatched fps causes audio-video desync.
- **Separate VAEs**: Audio VAE and video VAE are completely different models. Never swap their decode/encode nodes.
- **Frame count parity**: `EmptyLTXVLatentVideo.frame_count` and `EmptyLTXVAudioLatent.frame_count` must match exactly. The concat node will fail otherwise.
- **Latent dimensionality**: Video and audio latents have different channel counts. The concat node handles this internally but both must be valid LTXV latents.
- **Sample rate**: Audio VAE typically operates at 24kHz. Changing this requires a compatible audio VAE model.
- **VRAM**: Loading two VAE models increases memory usage. Consider offloading one VAE if VRAM is limited.
- **Seed coupling**: The same seed produces both video and audio from the fused latent. Different seeds produce mismatched outputs.
- **Post-processing**: After separation, video and audio can be independently processed (e.g., audio normalization, video upscaling) before final save.

## Example Widget Values

### Standard AV Generation

```
LTXVModelLoader: model_name = "ltxv-13b.safetensors"
LTXVAudioVAELoader: audio_vae_name = "ltxv_audio_vae.safetensors"
EmptyLTXVLatentVideo: width=480, height=256, frame_count=97
EmptyLTXVAudioLatent: frame_count=97, sample_rate=24000
LTXVConcatAVLatent: fps=24.0
KSampler: seed=42, steps=30, cfg=7.0, sampler_name="dpmpp_2m", scheduler="karras"
```

### With Audio Conditioning

```
LTXVAudioVAEEncode: frame_count=97
KSampler: steps=25, cfg=5.0
```
