# Wan Video Generation Pipeline

## When to Use

Generate video from text (t2v) or animate a still image (i2v) using Wan models. Supports frame count control and temporal conditioning. Use when you need high-quality video generation with Wan's native pipeline.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `WanModelLoader` | Load Wan diffusion model checkpoint |
| `WanCameraImageProvider` | Provide reference image for i2v (with camera metadata) |
| `LoadImage` | Alternative image loader for i2v without camera data |
| `WanTextEncode` | Encode text prompt into conditioning |
| `WanImageEncode` | Encode reference image for i2v conditioning |
| `WanSampler` | Denoise latent to generate video frames |
| `WanVaceCombine` | Combine VACE (Video Attention Conditioning Engine) outputs |
| `WanVideoDecoder` | Decode latent frames to pixel space |
| `VHS_VideoCombine` | Assemble frames into final video file |

## Connection Order

```
WanModelLoader
  ├── model        → WanSampler.model
  └── vae          → WanVideoDecoder.vae

WanTextEncode
  └── conditioning → WanSampler.positive

[For i2v only:]
WanCameraImageProvider (or LoadImage)
  └── image        → WanImageEncode.image
WanImageEncode
  └── conditioning → WanSampler.image_cond  (or WanVaceCombine)

WanSampler
  └── samples      → WanVideoDecoder.samples

WanVideoDecoder
  └── images       → VHS_VideoCombine.images

WanVaceCombine (optional, for VACE control)
  └── combined     → WanSampler.vace
```

## Node-by-Node Wiring Guide

### 1. WanModelLoader

Load the Wan model checkpoint.

```
Inputs:
  ckpt_name: "wan2.1_i2v_480p_14B_fp8.safetensors"  (widget)

Outputs:
  MODEL     → WanSampler
  CLIP      → WanTextEncode
  VAE       → WanVideoDecoder
```

### 2. WanTextEncode

Encode the text prompt for the Wan pipeline.

```
Inputs:
  text:   "a cat walking through a garden"           (widget, string)
  clip:   ← WanModelLoader.CLIP

Outputs:
  CONDITIONING → WanSampler.positive
```

Create a second `WanTextEncode` for negative prompt:

```
Inputs:
  text:   "blurry, distorted, low quality"            (widget, string)
  clip:   ← WanModelLoader.CLIP

Outputs:
  CONDITIONING → WanSampler.negative
```

### 3. WanCameraImageProvider / LoadImage (i2v only)

Provide the reference image to animate.

**WanCameraImageProvider:**
```
Inputs:
  image:       "reference.png"                        (widget, image upload)
  camera_data: {...}                                  (widget, JSON or preset)

Outputs:
  IMAGE         → WanImageEncode.image
  camera_embed  → WanSampler.camera_cond  (if supported)
```

**LoadImage (alternative):**
```
Inputs:
  image: "reference.png"                              (widget, image upload)

Outputs:
  IMAGE → WanImageEncode.image
```

### 4. WanImageEncode (i2v only)

Encode the reference image into conditioning for the sampler.

```
Inputs:
  image:  ← LoadImage.IMAGE or WanCameraImageProvider.IMAGE
  clip_vision: ← (from WanModelLoader or separate CLIPVisionLoader, if required)

Outputs:
  CONDITIONING → WanSampler.image_cond
```

### 5. WanSampler

Denoise latent to produce video frame latents.

```
Inputs:
  model:         ← WanModelLoader.MODEL
  positive:      ← WanTextEncode.positive
  negative:      ← WanTextEncode.negative (second instance)
  image_cond:    ← WanImageEncode.CONDITIONING  (i2v only, omit for t2v)
  vace:          ← WanVaceCombine.combined      (optional)
  camera_cond:   ← WanCameraImageProvider.camera_embed (optional)
  seed:          42                              (widget, int)
  steps:         30                              (widget, int)
  cfg:           6.0                             (widget, float)
  width:         832                             (widget, int)
  height:        480                             (widget, int)
  num_frames:    81                              (widget, int, must be 4n+1)

Outputs:
  LATENT → WanVideoDecoder.samples
```

### 6. WanVaceCombine (optional)

Combine multiple VACE control signals (mask, reference, etc.).

```
Inputs:
  vace_conditioning: ← (from VACE provider nodes)
  strength:          1.0                            (widget, float)

Outputs:
  COMBINED → WanSampler.vace
```

### 7. WanVideoDecoder

Decode latent frames into pixel images.

```
Inputs:
  samples: ← WanSampler.LATENT
  vae:     ← WanModelLoader.VAE

Outputs:
  IMAGES → VHS_VideoCombine.images
```

### 8. VHS_VideoCombine

Assemble decoded frames into a video file.

```
Inputs:
  images:        ← WanVideoDecoder.IMAGES
  frame_rate:    16                                (widget, int)
  loop_count:    0                                 (widget, int, 0 = no loop)
  format:        "video/h264-mp4"                  (widget, enum)
  save_output:   true                              (widget, bool)

Outputs:
  video_file:    (saved to output directory)
```

## Key Considerations

- **t2v vs i2v**: For text-to-video, omit the image encoding nodes. For image-to-video, include `LoadImage` + `WanImageEncode`.
- **Frame count**: Must be `4n + 1` (e.g., 81, 121, 161). Higher counts = longer video but more VRAM.
- **Resolution**: Wan i2v 480p expects 832×480 or 480×832. Do not exceed training resolution.
- **FP8 quantization**: Use `wan2.1_*_fp8.safetensors` for lower VRAM usage (~12 GB for 14B model).
- **Negative prompt**: Always provide a negative prompt for best quality.
- **CFG scale**: 5.0–7.0 is typical. Lower = more creative, higher = more faithful.
- **VACE**: Optional conditioning engine for masks, reference frames, and motion control. Only include if using VACE features.
- **Camera embedding**: `WanCameraImageProvider` supplies camera trajectory data for camera-controlled generation. Use `LoadImage` if camera control is not needed.

## Example Widget Values (t2v)

```
WanModelLoader:   ckpt_name = "wan2.1_t2v_480p_14B_fp8.safetensors"
WanTextEncode:    text = "a drone shot flying over a mountain range at sunset"
WanTextEncode:    text = "blurry, static, low quality"  (negative)
WanSampler:       seed=12345, steps=30, cfg=6.0, width=832, height=480, num_frames=81
VHS_VideoCombine: frame_rate=16, format="video/h264-mp4"
```

## Example Widget Values (i2v)

```
WanModelLoader:         ckpt_name = "wan2.1_i2v_480p_14B_fp8.safetensors"
WanCameraImageProvider: image = "photo.png"
WanTextEncode:          text = "the person slowly turns their head and smiles"
WanTextEncode:          text = "blurry, distorted"  (negative)
WanSampler:             seed=67890, steps=30, cfg=6.0, width=832, height=480, num_frames=81
VHS_VideoCombine:       frame_rate=16, format="video/h264-mp4"
```
