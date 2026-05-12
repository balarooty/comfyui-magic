# Dual Video Compare Pattern

## When to Use

Compare two video outputs side-by-side with synchronized playback. Use when evaluating different settings, models, prompts, or processing pipelines — see the visual differences in real time with frame-accurate alignment. Essential for A/B testing video generation parameters.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `DualVideoPreview` | Side-by-side comparison with slider and synced playback |
| `SaveVideo` (optional) | Save individual videos for external comparison |

## Connection Order

### Basic Comparison

```
# VIDEO A (e.g., different seed)
KSampler_A
  └── LATENT → VAEDecode_A.samples
VAEDecode_A
  └── IMAGE → DualVideoPreview.video_a

# VIDEO B (e.g., different prompt)
KSampler_B
  └── LATENT → VAEDecode_B.samples
VAEDecode_B
  └── IMAGE → DualVideoPreview.video_b

DualVideoPreview
  └── (terminal node — display only)
```

### File-Based Comparison

```
# Load from files
LoadVideo_A
  └── IMAGE → DualVideoPreview.video_a

LoadVideo_B
  └── IMAGE → DualVideoPreview.video_b

DualVideoPreview
  └── (terminal node — display only)
```

## Node-by-Node Wiring Guide

### 1. DualVideoPreview

```
Inputs:
  video_a:    ← VAEDecode_A.IMAGE or file path (IMAGE or STRING)
  video_b:    ← VAEDecode_B.IMAGE or file path (IMAGE or STRING)
  mute_a:     false                                (widget, bool)
  mute_b:     false                                (widget, bool)
  slider_pos: 0.5                                  (widget, float, 0.0-1.0)

Outputs:
  (none — terminal display node)
```

### 2. Video A Source

```
Inputs:
  samples: ← KSampler_A.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → DualVideoPreview.video_a
```

### 3. Video B Source

```
Inputs:
  samples: ← KSampler_B.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → DualVideoPreview.video_b
```

## Comparison Scenarios

### Different Seeds

```
KSampler_A: seed=42
KSampler_B: seed=12345

# Compare: How does seed affect composition?
```

### Different Prompts

```
CLIPTextEncode_A: text = "a cat sitting on a couch"
CLIPTextEncode_B: text = "a dog sitting on a couch"

# Compare: How does subject change affect the scene?
```

### Different Models

```
CheckpointLoaderSimple_A: ckpt_name = "model_v1.safetensors"
CheckpointLoaderSimple_B: ckpt_name = "model_v2.safetensors"

# Compare: How does model version affect quality?
```

### Different Samplers

```
KSampler_A: sampler_name = "dpmpp_2m", scheduler = "karras"
KSampler_B: sampler_name = "euler_ancestral", scheduler = "normal"

# Compare: How does sampler choice affect output?
```

### Different CFG Values

```
KSampler_A: cfg = 5.0
KSampler_B: cfg = 12.0

# Compare: How does CFG affect prompt adherence vs. quality?
```

### Base vs. Upscaled

```
Video A: Direct generation at target resolution
Video B: Low-res generation → latent upscale → refinement

# Compare: Is two-pass worth the extra time?
```

## Slider Behavior

The `slider_pos` widget controls the visual split:

| Value | Behavior |
|---|---|
| 0.0 | Show only Video A |
| 0.5 | Equal split (50/50) |
| 1.0 | Show only Video B |
| 0.0-0.3 | Video A dominant with sliver of B |
| 0.7-1.0 | Video B dominant with sliver of A |

The slider can be dragged interactively during playback.

## Audio Controls

| Widget | Effect |
|---|---|
| `mute_a = false` | Play audio from Video A |
| `mute_a = true` | Mute audio from Video A |
| `mute_b = false` | Play audio from Video B |
| `mute_b = true` | Mute audio from Video B |

- Only one audio source plays at a time by default
- Audio is synced to the video frame position
- Muting both produces silent playback

## Key Considerations

- **Terminal node**: `DualVideoPreview` has no outputs. It is a display-only node. To save videos, use separate `SaveVideo` nodes before the preview.
- **Frame count matching**: Both videos should have the same frame count. Mismatched frame counts cause playback desync — the shorter video loops or freezes.
- **Resolution matching**: Both videos should have the same resolution. Mismatched resolutions are displayed at their native size, which may not align visually.
- **Frame rate matching**: Both videos should use the same fps. Different fps causes one video to play faster than the other.
- **Synced playback**: Both videos play simultaneously, frame-locked. Scrubbing the timeline moves both videos to the same frame position.
- **Performance**: Playing two videos simultaneously requires more GPU memory for display. Reduce preview resolution if playback is choppy.
- **Memory**: Holding two full video frame arrays in RAM doubles memory usage compared to a single preview. For long videos (>300 frames), consider using file-based loading.
- **File path input**: `DualVideoPreview` accepts file paths (STRING) instead of frame arrays (IMAGE). Use this for comparing previously saved videos without regenerating.
- **Export**: Some hosts allow exporting the side-by-side comparison as a single video file. Check your host's export options.

## Example Widget Values

### Seed Comparison

```
DualVideoPreview:
  video_a: ← KSampler_A (seed=42)
  video_b: ← KSampler_B (seed=12345)
  mute_a: false
  mute_b: false
  slider_pos: 0.5
```

### Model Comparison

```
DualVideoPreview:
  video_a: ← model_v1 output
  video_b: ← model_v2 output
  mute_a: true
  mute_b: true
  slider_pos: 0.5
```

### File-Based Comparison

```
DualVideoPreview:
  video_a: "/path/to/output_a.mp4"
  video_b: "/path/to/output_b.mp4"
  slider_pos: 0.5
```
