# LoRA Stacking and Merging

## When to Use

Apply multiple LoRA (Low-Rank Adaptation) models to a base checkpoint. Each LoRA modifies the model and/or CLIP behavior. Use when combining multiple style, character, or concept LoRAs to achieve a composite effect.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Load base diffusion model |
| `LoraLoader` | Apply a single LoRA (chain multiple for stacking) |
| `CLIPTextEncode` | Encode text prompt through LoRA-modified CLIP |
| `EmptyLatentImage` | Create blank latent |
| `KSampler` | Denoise latent |
| `VAEDecode` | Decode latent to pixel image |
| `SaveImage` | Save final output |

## Connection Order

```
CheckpointLoaderSimple
  ├── model → LoraLoader_1.model
  ├── clip  → LoraLoader_1.clip
  └── vae   → VAEDecode.vae

LoraLoader_1
  ├── MODEL → LoraLoader_2.model
  └── CLIP  → LoraLoader_2.clip

LoraLoader_2
  ├── MODEL → LoraLoader_3.model  (or → KSampler.model if last)
  └── CLIP  → LoraLoader_3.clip   (or → CLIPTextEncode.clip if last)

LoraLoader_3 (last in chain)
  ├── MODEL → KSampler.model
  └── CLIP  → CLIPTextEncode.clip

CLIPTextEncode (positive)
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
  ckpt_name: "juggernautXL_v9.safetensors"          (widget, model file)

Outputs:
  MODEL → LoraLoader_1.model
  CLIP  → LoraLoader_1.clip
  VAE   → VAEDecode.vae
```

### 2. LoraLoader_1 (first LoRA)

```
Inputs:
  model:          ← CheckpointLoaderSimple.MODEL
  clip:           ← CheckpointLoaderSimple.CLIP
  lora_name:      "style_watercolor.safetensors"    (widget, LoRA file)
  strength_model: 0.8                              (widget, float, -10 to 10)
  strength_clip:  0.8                              (widget, float, -10 to 10)

Outputs:
  MODEL → LoraLoader_2.model
  CLIP  → LoraLoader_2.clip
```

### 3. LoraLoader_2 (second LoRA)

```
Inputs:
  model:          ← LoraLoader_1.MODEL
  clip:           ← LoraLoader_1.CLIP
  lora_name:      "character_anna_v2.safetensors"   (widget, LoRA file)
  strength_model: 0.7                              (widget, float)
  strength_clip:  0.7                              (widget, float)

Outputs:
  MODEL → LoraLoader_3.model
  CLIP  → LoraLoader_3.clip
```

### 4. LoraLoader_3 (third LoRA — last in chain)

```
Inputs:
  model:          ← LoraLoader_2.MODEL
  clip:           ← LoraLoader_2.CLIP
  lora_name:      "detail_enhancer.safetensors"     (widget, LoRA file)
  strength_model: 0.5                              (widget, float)
  strength_clip:  0.5                              (widget, float)

Outputs:
  MODEL → KSampler.model
  CLIP  → CLIPTextEncode.clip
```

### 5. CLIPTextEncode (positive)

```
Inputs:
  text: "anna in a watercolor style garden, highly detailed"
  clip: ← LoraLoader_3.CLIP   (uses LoRA-modified CLIP)

Outputs:
  CONDITIONING → KSampler.positive
```

### 6. CLIPTextEncode (negative)

```
Inputs:
  text: "blurry, low quality, deformed"
  clip: ← LoraLoader_3.CLIP   (uses LoRA-modified CLIP)

Outputs:
  CONDITIONING → KSampler.negative
```

### 7. EmptyLatentImage

```
Inputs:
  width:      1024                                (widget, int)
  height:     1024                                (widget, int)
  batch_size: 1                                   (widget, int)

Outputs:
  LATENT → KSampler.latent_image
```

### 8. KSampler

```
Inputs:
  model:        ← LoraLoader_3.MODEL
  positive:     ← CLIPTextEncode.positive
  negative:     ← CLIPTextEncode.negative
  latent_image: ← EmptyLatentImage.LATENT
  seed:         42                                (widget, int)
  steps:        30                                (widget, int)
  cfg:          7.0                               (widget, float)
  sampler_name: "dpmpp_2m"                        (widget, enum)
  scheduler:    "karras"                          (widget, enum)

Outputs:
  LATENT → VAEDecode.samples
```

### 9. VAEDecode

```
Inputs:
  samples: ← KSampler.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → SaveImage.images
```

### 10. SaveImage

```
Inputs:
  images: ← VAEDecode.IMAGE
  filename_prefix: "lora_stacked"
```

## Strength Tuning Guide

| strength_model | strength_clip | Effect |
|---|---|---|
| 1.0 | 1.0 | Full LoRA effect on both model and text encoding |
| 0.7 | 0.7 | Moderate effect — good default for stacking |
| 0.5 | 0.5 | Subtle effect — allows other LoRAs to dominate |
| 1.0 | 0.0 | LoRA affects generation only, not prompt understanding |
| 0.0 | 1.0 | LoRA affects prompt understanding only, not generation |
| -1.0 | -1.0 | Inverts the LoRA effect (negative LoRA) |

## Key Considerations

- **Chain order matters**: LoRAs are applied sequentially. The first LoRA modifies the base model, the second modifies the already-modified model, and so on. Changing order changes the result.
- **strength_model vs strength_clip**: `strength_model` controls how much the LoRA affects the diffusion model's denoising behavior. `strength_clip` controls how much it affects the text encoder's understanding of trigger words.
- **Diminishing returns**: Stacking 3+ LoRAs often requires reducing individual strengths to avoid artifacts. Start at 0.5–0.7 each.
- **Conflict resolution**: Two LoRAs targeting the same layers will interfere. If one LoRA is for style and another for character, they typically compose well. Two style LoRAs will fight.
- **VRAM**: Each loaded LoRA increases memory usage. Chain them — don't load the same LoRA twice.
- **Negative strengths**: Using negative `strength_model` or `strength_clip` inverts the LoRA effect. Useful for removing concepts or creating contrast.
- **LoRA compatibility**: Ensure LoRA files match the base model architecture (SD1.5 LoRAs won't work on SDXL, etc.).
- **Clip skip**: Some LoRAs are trained with specific clip skip values. Match `CLIPTextEncode` or `CLIPSetLastLayer` settings to the LoRA's training config.

## Example Widget Values

### Style + Character Stacking

```
CheckpointLoaderSimple: ckpt_name = "dreamshaperXL_v21.safetensors"
LoraLoader_1: lora_name = "oil_painting_style.safetensors", strength_model=0.6, strength_clip=0.6
LoraLoader_2: lora_name = "character_elena_v1.safetensors", strength_model=0.8, strength_clip=0.8
LoraLoader_3: lora_name = "film_grain_v1.safetensors", strength_model=0.3, strength_clip=0.0
CLIPTextEncode: text = "elena standing in a garden, oil painting style, masterpiece"
KSampler: seed=42, steps=30, cfg=7.0, sampler_name="dpmpp_2m", scheduler="karras"
```

### Double Style Blend

```
CheckpointLoaderSimple: ckpt_name = "sd_xl_base_1.0.safetensors"
LoraLoader_1: lora_name = "anime_style_v3.safetensors", strength_model=0.5, strength_clip=0.5
LoraLoader_2: lora_name = "cyberpunk_neon_v1.safetensors", strength_model=0.5, strength_clip=0.5
CLIPTextEncode: text = "a cyberpunk city street, anime style, neon lights"
KSampler: seed=99, steps=30, cfg=7.5
```
