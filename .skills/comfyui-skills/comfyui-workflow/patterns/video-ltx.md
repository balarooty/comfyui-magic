# LTX Video Generation Pipeline

## When to Use

Generate video using LTX (Latent Transfer eXchange) video models. LTX uses a video-specific latent space where the frame dimension is part of the latent tensor. Use when working with LTX checkpoints for text-to-video generation.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `LTXVLoader` | Load LTX video model checkpoint |
| `CLIPTextEncode` | Encode text prompt into conditioning |
| `EmptyLatentImage` | Create latent tensor with video frame dimension |
| `LTXVSampler` | Denoise latent to generate video frames |
| `VAEDecode` | Decode latent to pixel images |
| `VHS_VideoCombine` | Assemble frames into final video file |

## Connection Order

```
LTXVLoader
  ├── model → LTXVSampler.model
  ├── clip  → CLIPTextEncode (positive + negative)
  └── vae   → VAEDecode.vae

CLIPTextEncode (positive)
  └── CONDITIONING → LTXVSampler.positive

CLIPTextEncode (negative)
  └── CONDITIONING → LTXVSampler.negative

EmptyLatentImage
  └── LATENT → LTXVSampler.latent_image

LTXVSampler
  └── LATENT → VAEDecode.samples

VAEDecode
  └── IMAGE → VHS_VideoCombine.images

VHS_VideoCombine
  └── video_file → (output)
```

## Node-by-Node Wiring Guide

### 1. LTXVLoader

Load the LTX video model.

```
Inputs:
  ckpt_name: "ltx-video-2b-fp16.safetensors"     (widget, model file)

Outputs:
  MODEL → LTXVSampler.model
  CLIP  → CLIPTextEncode.clip
  VAE   → VAEDecode.vae
```

### 2. CLIPTextEncode (positive)

Encode the positive text prompt.

```
Inputs:
  text: "a timelapse of flowers blooming in a garden"  (widget, string)
  clip: ← LTXVLoader.CLIP

Outputs:
  CONDITIONING → LTXVSampler.positive
```

### 3. CLIPTextEncode (negative)

Encode the negative text prompt.

```
Inputs:
  text: "static, blurry, distorted, low resolution"    (widget, string)
  clip: ← LTXVLoader.CLIP

Outputs:
  CONDITIONING → LTXVSampler.negative
```

### 4. EmptyLatentImage

Create the initial latent tensor. For LTX video, the height represents `(frames × spatial_height)` compressed into the latent.

```
Inputs:
  width:    768                                (widget, int)
  height:   512                                (widget, int) — see note below
  batch_size: 1                                (widget, int)

Outputs:
  LATENT → LTXVSampler.latent_image
```

**Important**: LTX encodes the temporal dimension into the latent height. Use a combined height value:
- `height = spatial_height_p × frames_p / compression_factor`
- For 25 frames at 480p: `height = 480/8 × 25/8 ≈ 512` (actual formula depends on model version)
- Check model documentation for exact latent dimensions per frame count.

### 5. LTXVSampler

Denoise the latent to produce video frames.

```
Inputs:
  model:          ← LTXVLoader.MODEL
  positive:       ← CLIPTextEncode.positive (positive instance)
  negative:       ← CLIPTextEncode.negative (negative instance)
  latent_image:   ← EmptyLatentImage.LATENT
  seed:           42                       (widget, int)
  steps:          25                       (widget, int)
  cfg:            7.0                      (widget, float)
  scheduler:      "normal"                 (widget, enum)
  sampler_name:   "euler"                  (widget, enum)

Outputs:
  LATENT → VAEDecode.samples
```

### 6. VAEDecode

Decode the latent into pixel images.

```
Inputs:
  samples: ← LTXVSampler.LATENT
  vae:     ← LTXVLoader.VAE

Outputs:
  IMAGE → VHS_VideoCombine.images
```

### 7. VHS_VideoCombine

Assemble decoded frames into a video file.

```
Inputs:
  images:      ← VAEDecode.IMAGE
  frame_rate:  24                            (widget, int)
  loop_count:  0                             (widget, int)
  format:      "video/h264-mp4"             (widget, enum)
  save_output: true                          (widget, bool)

Outputs:
  video_file:  (saved to output directory)
```

## Key Considerations

- **Latent space**: LTX encodes temporal information in the latent tensor. The `EmptyLatentImage` height is not the output image height — it encodes both spatial and temporal dimensions.
- **Frame count**: Determined by the latent height and the model's temporal compression ratio. Typical: 25 frames (≈1s at 24fps), 81 frames (≈3.4s).
- **Resolution**: LTX 2B supports 768×512, 512×768, and similar. Do not exceed training resolution.
- **FP16 vs FP8**: Use FP16 for quality, FP8 for lower VRAM (~8 GB for 2B model).
- **CFG scale**: 5.0–9.0 typical. Lower values = more motion, higher = more stable.
- **Samplers**: `euler` with `normal` scheduler works well. `euler_ancestral` adds more variation.
- **Prompt**: LTX responds well to descriptive prompts. Include motion descriptors ("timelapse", "slowly panning", "walking").
- **No native i2v**: LTX does not have a built-in image-to-video path. Use img2img-style workflows or control adapters if needed.

## Example Widget Values

```
LTXVLoader:       ckpt_name = "ltx-video-2b-fp16.safetensors"
CLIPTextEncode:   text = "a golden retriever running through autumn leaves, cinematic lighting"
CLIPTextEncode:   text = "static, blurry, distorted"  (negative)
EmptyLatentImage: width=768, height=512, batch_size=1
LTXVSampler:      seed=42, steps=25, cfg=7.0, scheduler="normal", sampler_name="euler"
VHS_VideoCombine: frame_rate=24, format="video/h264-mp4"
```
