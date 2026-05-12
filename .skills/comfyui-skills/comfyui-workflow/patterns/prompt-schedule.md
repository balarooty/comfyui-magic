# Prompt Scheduling / Temporal Conditioning

## When to Use

Apply different prompts at different stages of the sampling process. Enables style transitions, concept blending, and progressive detail injection. Use when a single prompt cannot express the desired output, or when you want to control the evolution of the image during denoising.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Load base diffusion model |
| `CLIPTextEncode` | Encode each prompt variant |
| `PromptSchedule` | Define which prompt is active at which step |
| `KSampler` | Denoise with scheduled conditioning |
| `VAEDecode` | Decode latent to pixel image |
| `SaveImage` | Save final output |

## Connection Order

```
CheckpointLoaderSimple
  ├── model → KSampler.model
  ├── clip  → CLIPTextEncode (all instances)
  └── vae   → VAEDecode.vae

CLIPTextEncode (prompt 1)
  └── CONDITIONING → PromptSchedule

CLIPTextEncode (prompt 2)
  └── CONDITIONING → PromptSchedule

PromptSchedule
  └── CONDITIONING → KSampler.positive

CLIPTextEncode (negative)
  └── CONDITIONING → KSampler.negative

EmptyLatentImage
  └── LATENT → KSampler.latent_image

KSampler
  └── LATENT → VAEDecode.samples

VAEDecode
  └── IMAGE → SaveImage.images
```

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple

```
Inputs:
  ckpt_name: "juggernautXL_v9.safetensors"           (widget, model file)

Outputs:
  MODEL → KSampler.model
  CLIP  → CLIPTextEncode.clip (all instances)
  VAE   → VAEDecode.vae
```

### 2. CLIPTextEncode (Prompt 1 — early steps)

```
Inputs:
  text: "a serene mountain landscape at dawn, soft pastel colors"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → PromptSchedule.cond_1
```

### 3. CLIPTextEncode (Prompt 2 — late steps)

```
Inputs:
  text: "a dramatic mountain landscape at sunset, vibrant orange and purple sky, hyper detailed"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → PromptSchedule.cond_2
```

### 4. CLIPTextEncode (Negative)

```
Inputs:
  text: "blurry, low quality, distorted"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → KSampler.negative
```

### 5. PromptSchedule

Define step ranges for each prompt.

```
Inputs:
  cond_1:    ← CLIPTextEncode (prompt 1).CONDITIONING
  cond_2:    ← CLIPTextEncode (prompt 2).CONDITIONING
  schedule:  "0:15,15:30"                            (widget, string)
             ↑       ↑
             |       └── Steps 15–29: use prompt 2
             └── Steps 0–14: use prompt 1

  total_steps: 30                                    (widget, int)

Outputs:
  CONDITIONING → KSampler.positive
```

**Schedule format**: `"start:end,start:end,..."` where numbers are step indices. Each segment maps to a corresponding conditioning input.

### 6. KSampler

```
Inputs:
  model:        ← CheckpointLoaderSimple.MODEL
  positive:     ← PromptSchedule.CONDITIONING
  negative:     ← CLIPTextEncode (negative).CONDITIONING
  latent_image: ← EmptyLatentImage.LATENT
  seed:         42                                   (widget, int)
  steps:        30                                   (widget, int)
  cfg:          7.0                                  (widget, float)
  sampler_name: "dpmpp_2m"                           (widget, enum)
  scheduler:    "karras"                             (widget, enum)

Outputs:
  LATENT → VAEDecode.samples
```

### 7. EmptyLatentImage

```
Inputs:
  width:      1024                                 (widget, int)
  height:     1024                                 (widget, int)
  batch_size: 1                                    (widget, int)

Outputs:
  LATENT → KSampler.latent_image
```

### 8. VAEDecode

```
Inputs:
  samples: ← KSampler.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → SaveImage.images
```

### 9. SaveImage

```
Inputs:
  images: ← VAEDecode.IMAGE
  filename_prefix: "scheduled"                     (widget, string)
```

## Advanced Scheduling Patterns

### Multi-Prompt Blending (3+ prompts)

Chain multiple `PromptSchedule` nodes or use a single node with 3+ conditioning inputs:

```
CLIPTextEncode (prompt A) → PromptSchedule.cond_1
CLIPTextEncode (prompt B) → PromptSchedule.cond_2
CLIPTextEncode (prompt C) → PromptSchedule.cond_3

PromptSchedule: schedule = "0:10,10:20,20:30"
```

### Attention-Based Scheduling

Use `CLIPTextEncode` with different token weights that change over steps:

```
Prompt 1 (early):  "a (photo:1.2) of a cat"
Prompt 2 (late):   "a (painting:1.5) of a cat"
Schedule: "0:15,15:30"
```

### Conditioning Multiplier Scheduling

Some scheduling nodes support per-step conditioning strength:

```
cond_1_strength: "1.0:0.3"    (fades from 1.0 to 0.3 over steps)
cond_2_strength: "0.3:1.0"    (rises from 0.3 to 1.0 over steps)
```

## Key Considerations

- **Step boundaries**: The schedule `"0:15,15:30"` with 30 total steps means prompt 1 dominates the structure (early denoising) and prompt 2 refines details (late denoising).
- **Early steps = structure**: Steps 0–30% establish composition, layout, and major shapes.
- **Mid steps = detail**: Steps 30–70% add texture, color, and secondary features.
- **Late steps = refinement**: Steps 70–100% polish and add fine details.
- **Smooth transitions**: Use overlapping step ranges or blended schedules for gradual transitions.
- **CFG interaction**: High CFG amplifies prompt differences between steps. Lower CFG smooths transitions.
- **Seed sensitivity**: Different seeds produce different transitions for the same schedule. Pin seeds for reproducibility.
- **Multiple schedulers**: Some scheduling nodes support per-concept scheduling (e.g., style at step 10, subject at step 5). Check node documentation.

## Example Widget Values

### Style Transition

```
CheckpointLoaderSimple: ckpt_name = "sd_xl_base_1.0.safetensors"
CLIPTextEncode:  text = "a landscape photograph, realistic, detailed"     (prompt 1)
CLIPTextEncode:  text = "a landscape oil painting, impressionist style"   (prompt 2)
CLIPTextEncode:  text = "blurry, ugly"                                    (negative)
PromptSchedule:  schedule = "0:20,20:40", total_steps = 40
KSampler:        seed=42, steps=40, cfg=7.5, sampler_name="dpmpp_2m", scheduler="karras"
EmptyLatentImage: width=1024, height=1024, batch_size=1
```

### Concept Blending

```
CLIPTextEncode:  text = "a red sports car"                    (prompt 1)
CLIPTextEncode:  text = "a futuristic flying vehicle"         (prompt 2)
PromptSchedule:  schedule = "0:12,12:25", total_steps = 25
KSampler:        steps=25, cfg=7.0
```
