# Audio-Reactive Generation

## When to Use

Generate images or video that react to audio features — amplitude, frequency, beat, onset. Audio drives generation parameters like prompt strength, CFG, seed, or conditioning, creating synchronized visual-audio output. Use for music visualizers, beat-synced animations, and audio-driven art.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `LoadAudio` | Load audio file |
| `AudioAnalysis` | Extract audio features (amplitude, frequency, beat, onset) |
| `AudioScheduler` | Map audio features to scheduling values per frame |
| `ConditioningFromSchedule` | Apply scheduled values to conditioning |
| `CheckpointLoaderSimple` | Load base diffusion model |
| `CLIPTextEncode` | Encode text prompt |
| `EmptyLatentImage` | Create latent (batch for video frames) |
| `KSampler` | Denoise each frame |
| `VAEDecode` | Decode latent to pixel |
| `SaveImage` | Save single frame |
| `VHS_VideoCombine` | Assemble frames into video |

## Connection Order

```
LoadAudio
  └── audio → AudioAnalysis.audio

AudioAnalysis
  ├── amplitude → AudioScheduler.amplitude
  ├── frequency → AudioScheduler.frequency
  ├── beat      → AudioScheduler.beat
  └── onset     → AudioScheduler.onset

AudioScheduler
  └── schedule  → ConditioningFromSchedule.schedule

CheckpointLoaderSimple
  ├── model → KSampler.model
  ├── clip  → CLIPTextEncode.clip
  └── vae   → VAEDecode.vae

CLIPTextEncode
  └── CONDITIONING → ConditioningFromSchedule.conditioning

ConditioningFromSchedule
  └── CONDITIONING → KSampler.positive

EmptyLatentImage (batch_size = frame count)
  └── LATENT → KSampler.latent_image

KSampler
  └── LATENT → VAEDecode.samples

VAEDecode
  └── IMAGE → VHS_VideoCombine.images
```

## Node-by-Node Wiring Guide

### 1. LoadAudio

```
Inputs:
  audio: "song.mp3"                                  (widget, audio file upload)

Outputs:
  AUDIO → AudioAnalysis.audio
  audio_file: "song.mp3"                             (metadata)
```

### 2. AudioAnalysis

Extract features from the audio signal.

```
Inputs:
  audio:        ← LoadAudio.AUDIO
  fps:          24                                   (widget, int — output frames per second)
  fft_size:     2048                                 (widget, int — FFT window size)
  hop_length:   512                                  (widget, int — hop between FFT windows)

Outputs:
  AMPLITUDE     → AudioScheduler.amplitude     (float per frame, 0.0–1.0)
  FREQUENCY     → AudioScheduler.frequency     (float per frame, 0.0–1.0, normalized)
  BEAT          → AudioScheduler.beat          (binary per frame, 0 or 1)
  ONSET         → AudioScheduler.onset         (float per frame, 0.0–1.0, onset strength)
  RMS           → (root mean square energy per frame)
  SPECTRAL_CENTROID → (brightness per frame)
```

### 3. AudioScheduler

Map audio features to per-frame scheduling values.

```
Inputs:
  amplitude:      ← AudioAnalysis.AMPLITUDE
  frequency:      ← AudioAnalysis.FREQUENCY
  beat:           ← AudioAnalysis.BEAT
  onset:          ← AudioAnalysis.ONSET
  mapping_mode:   "amplitude"                        (widget, enum: "amplitude", "frequency", "beat", "onset", "custom")
  min_value:      0.0                                (widget, float — schedule floor)
  max_value:      1.0                                (widget, float — schedule ceiling)
  smoothing:      0.3                                (widget, float — temporal smoothing factor)
  beat_boost:     2.0                                (widget, float — multiplier on beat frames)

Outputs:
  SCHEDULE → ConditioningFromSchedule.schedule
```

### 4. ConditioningFromSchedule

Apply the audio-driven schedule to a conditioning signal.

```
Inputs:
  conditioning: ← CLIPTextEncode.CONDITIONING
  schedule:     ← AudioScheduler.SCHEDULE
  target_field: "strength"                           (widget, enum: "strength", "cfg", "sigma_shift")

Outputs:
  CONDITIONING → KSampler.positive
```

### 5. CheckpointLoaderSimple

```
Inputs:
  ckpt_name: "dreamshaperXL_v21.safetensors"        (widget, model file)

Outputs:
  MODEL → KSampler.model
  CLIP  → CLIPTextEncode.clip
  VAE   → VAEDecode.vae
```

### 6. CLIPTextEncode

```
Inputs:
  text: "an abstract colorful explosion of energy, vibrant, dynamic"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → ConditioningFromSchedule.conditioning
```

### 7. EmptyLatentImage

Create a batch of latents — one per frame.

```
Inputs:
  width:      1024                                 (widget, int)
  height:     576                                  (widget, int)
  batch_size: 240                                  (widget, int — total frames, e.g. 10s × 24fps)

Outputs:
  LATENT → KSampler.latent_image
```

### 8. KSampler

```
Inputs:
  model:        ← CheckpointLoaderSimple.MODEL
  positive:     ← ConditioningFromSchedule.CONDITIONING
  negative:     ← CLIPTextEncode (negative).CONDITIONING
  latent_image: ← EmptyLatentImage.LATENT
  seed:         42                                 (widget, int)
  steps:        20                                 (widget, int — lower for speed)
  cfg:          7.0                                (widget, float)
  sampler_name: "dpmpp_2m"                         (widget, enum)
  scheduler:    "karras"                           (widget, enum)

Outputs:
  LATENT → VAEDecode.samples
```

### 9. VAEDecode

```
Inputs:
  samples: ← KSampler.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → VHS_VideoCombine.images
```

### 10. VHS_VideoCombine

```
Inputs:
  images:      ← VAEDecode.IMAGE
  frame_rate:  24                                  (widget, int — must match AudioAnalysis fps)
  loop_count:  0                                   (widget, int)
  format:      "video/h264-mp4"                    (widget, enum)
  save_output: true                                (widget, bool)

Outputs:
  video_file:  (saved to output directory)
```

## Audio-to-Visual Mapping Strategies

### Amplitude → Generation Strength

Louder passages produce more detailed/intense visuals. Quieter passages are softer.

```
AudioScheduler: mapping_mode="amplitude", min_value=0.3, max_value=1.0
ConditioningFromSchedule: target_field="strength"
```

### Beat → Seed Change

Each beat triggers a new random seed, creating visual shifts on the beat.

```
AudioScheduler: mapping_mode="beat", beat_boost=1.0
# Connect beat output to a seed modulation node (custom)
```

### Frequency → Color Temperature

Map low frequencies to warm tones, high frequencies to cool tones via prompt scheduling.

```
AudioScheduler: mapping_mode="frequency", min_value=0.0, max_value=1.0
# Use schedule to blend between "warm red tones" (low freq) and "cool blue tones" (high freq)
```

### Onset → Style Change

Sudden sounds trigger style transitions via prompt blending.

```
AudioScheduler: mapping_mode="onset", smoothing=0.1, beat_boost=3.0
ConditioningFromSchedule: target_field="strength"
```

## Key Considerations

- **FPS alignment**: `AudioAnalysis.fps` must match `VHS_VideoCombine.frame_rate`. Mismatch causes audio-visual desync.
- **Batch size**: Set `EmptyLatentImage.batch_size` to `duration_seconds × fps`. For a 10s clip at 24fps: `batch_size = 240`.
- **VRAM**: Batch generation is memory-intensive. Reduce resolution or use sequential sampling for long clips.
- **Smoothing**: High smoothing (0.5–0.9) creates gentle transitions. Low smoothing (0.0–0.2) creates sharp, reactive changes.
- **Beat detection**: `AudioAnalysis.beat` output is binary. Use `beat_boost` to amplify beat frames in the schedule.
- **Steps tradeoff**: Lower steps (15–20) enable faster iteration for video. Higher steps (30+) for final quality.
- **Seed consistency**: Keeping the same seed across frames maintains visual coherence. Changing seed on beats creates deliberate discontinuities.
- **Target field**: `strength` modulates conditioning intensity. `cfg` modulates classifier-free guidance. Choose based on what you want audio to control.
- **Custom audio nodes**: The exact node names (`AudioAnalysis`, `AudioScheduler`, `ConditioningFromSchedule`) may vary by custom node pack. Check your installed audio-reactive nodes for exact names.

## Example Widget Values

### Beat-Synced Visualizer

```
LoadAudio: audio = "edm_track.mp3"
AudioAnalysis: fps=24, fft_size=2048, hop_length=512
AudioScheduler: mapping_mode="beat", min_value=0.4, max_value=1.0, smoothing=0.2, beat_boost=2.5
ConditioningFromSchedule: target_field="strength"
CLIPTextEncode: text = "abstract geometric patterns, neon colors, explosive energy"
EmptyLatentImage: width=1024, height=576, batch_size=240
KSampler: seed=42, steps=20, cfg=7.0
VHS_VideoCombine: frame_rate=24, format="video/h264-mp4"
```

### Amplitude-Driven Landscape

```
LoadAudio: audio = "ambient_pad.wav"
AudioAnalysis: fps=16, fft_size=4096, hop_length=1024
AudioScheduler: mapping_mode="amplitude", min_value=0.2, max_value=0.9, smoothing=0.7, beat_boost=1.0
ConditioningFromSchedule: target_field="strength"
CLIPTextEncode: text = "a serene landscape that breathes with the music, soft light"
EmptyLatentImage: width=1024, height=576, batch_size=160
KSampler: seed=123, steps=25, cfg=6.5
VHS_VideoCombine: frame_rate=16, format="video/h264-mp4"
```
