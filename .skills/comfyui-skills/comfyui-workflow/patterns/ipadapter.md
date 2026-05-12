# IP-Adapter Image Conditioning

## When to Use

Inject visual features from a reference image into the generation process. IP-Adapter extracts CLIP vision features from an image and uses them to condition the diffusion model. Use for style transfer, character consistency, composition guidance, or visual prompt augmentation without fine-tuning.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Load base diffusion model |
| `CLIPVisionLoader` | Load CLIP vision encoder for image feature extraction |
| `IPAdapterModelLoader` | Load IP-Adapter model weights |
| `IPAdapterApply` | Apply IP-Adapter conditioning to the model |
| `LoadImage` | Load reference image(s) |
| `CLIPTextEncode` | Encode text prompt |
| `EmptyLatentImage` | Create blank latent |
| `KSampler` | Denoise latent |
| `VAEDecode` | Decode latent to pixel image |
| `SaveImage` | Save final output |

## Connection Order

```
CheckpointLoaderSimple
  ├── model → IPAdapterApply.model
  └── vae   → VAEDecode.vae

CLIPVisionLoader
  └── clip_vision → IPAdapterApply.clip_vision

IPAdapterModelLoader
  └── ipadapter → IPAdapterApply.ipadapter

LoadImage (reference)
  └── image → IPAdapterApply.image

IPAdapterApply
  └── MODEL → KSampler.model

CLIPTextEncode (positive)
  └── CONDITIONING → KSampler.positive

CLIPTextEncode (negative)
  └── CONDITIONING → KSampler.negative

CheckpointLoaderSimple
  └── clip → CLIPTextEncode.clip (both positive and negative)

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
  MODEL → IPAdapterApply.model
  CLIP  → CLIPTextEncode.clip (positive + negative)
  VAE   → VAEDecode.vae
```

### 2. CLIPVisionLoader

Load the CLIP vision model used by the IP-Adapter.

```
Inputs:
  clip_name: "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"  (widget, vision model)
             — or —
  clip_name: "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"  (for SDXL IP-Adapter)

Outputs:
  CLIP_VISION → IPAdapterApply.clip_vision
```

### 3. IPAdapterModelLoader

Load the IP-Adapter model weights.

```
Inputs:
  ipadapter_file: "ip-adapter-plus_sdxl_vit-h.safetensors"  (widget, IP-Adapter file)
                  — or —
  ipadapter_file: "ip-adapter_sd15.safetensors"              (for SD1.5)

Outputs:
  IPADAPTER → IPAdapterApply.ipadapter
```

### 4. LoadImage

Load the reference image whose features will guide generation.

```
Inputs:
  image: "reference_photo.png"                       (widget, image upload)

Outputs:
  IMAGE → IPAdapterApply.image
```

### 5. IPAdapterApply

Apply the IP-Adapter conditioning to the model.

```
Inputs:
  model:       ← CheckpointLoaderSimple.MODEL
  ipadapter:   ← IPAdapterModelLoader.IPADAPTER
  clip_vision: ← CLIPVisionLoader.CLIP_VISION
  image:       ← LoadImage.IMAGE
  weight:      0.8                                   (widget, float, 0.0 to 2.0)
  noise:       0.0                                   (widget, float, 0.0 to 1.0)
  weight_type: "original"                            (widget, enum: "original", "linear", "ease in", "ease out", "ease in-out", "rev eee")
  start_at:    0.0                                   (widget, float, 0.0 to 1.0)
  end_at:      1.0                                   (widget, float, 0.0 to 1.0)

Outputs:
  MODEL → KSampler.model
```

### 6. CLIPTextEncode (positive)

```
Inputs:
  text: "a portrait of a person in a dramatic cinematic style"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → KSampler.positive
```

### 7. CLIPTextEncode (negative)

```
Inputs:
  text: "blurry, low quality, deformed, ugly"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → KSampler.negative
```

### 8. EmptyLatentImage

```
Inputs:
  width:      1024                                 (widget, int)
  height:     1024                                 (widget, int)
  batch_size: 1                                    (widget, int)

Outputs:
  LATENT → KSampler.latent_image
```

### 9. KSampler

```
Inputs:
  model:        ← IPAdapterApply.MODEL
  positive:     ← CLIPTextEncode.positive
  negative:     ← CLIPTextEncode.negative
  latent_image: ← EmptyLatentImage.LATENT
  seed:         42                                 (widget, int)
  steps:        30                                 (widget, int)
  cfg:          7.0                                (widget, float)
  sampler_name: "dpmpp_2m"                         (widget, enum)
  scheduler:    "karras"                           (widget, enum)

Outputs:
  LATENT → VAEDecode.samples
```

### 10. VAEDecode

```
Inputs:
  samples: ← KSampler.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → SaveImage.images
```

### 11. SaveImage

```
Inputs:
  images: ← VAEDecode.IMAGE
  filename_prefix: "ipadapter_output"
```

## Advanced Patterns

### Multiple Reference Images

Chain `IPAdapterApply` nodes for multiple references:

```
LoadImage_1 → IPAdapterApply_1 (weight=0.6) → IPAdapterApply_2 (weight=0.4) ← LoadImage_2
```

Or use `IPAdapterCombine` if available:

```
LoadImage_1 → IPAdapterCombine.image_1
LoadImage_2 → IPAdapterCombine.image_2
IPAdapterCombine → IPAdapterApply.image
```

### IP-Adapter + LoRA

Apply IP-Adapter before LoRA (IP-Adapter patches the model, LoRA modifies it further):

```
CheckpointLoaderSimple → IPAdapterApply → LoraLoader → KSampler
```

### Face ID / Face Consistency

Use `IPAdapterApplyFaceID` (if available) with a face reference:

```
LoadImage (face photo) → IPAdapterApplyFaceID.image
IPAdapterApplyFaceID: weight=1.0, weight_type="original"
```

## IP-Adapter Weight Types

| weight_type | Behavior |
|---|---|
| `original` | Standard IP-Adapter influence — consistent throughout sampling |
| `linear` | Linearly increases influence from start_at to end_at |
| `ease in` | Slow start, strong finish — IP-Adapter influence ramps up |
| `ease out` | Fast start, gentle finish — IP-Adapter influence fades |
| `ease in-out` | Bell curve — ramps up then down |
| `rev eee` | Reverse bell curve — strong at edges, weak in middle |

## Key Considerations

- **Weight**: `0.5–1.0` is typical. Values above 1.0 amplify the reference image's influence, potentially overriding the text prompt.
- **Noise**: Adds stochastic variation to the image features. `0.0–0.1` is typical. Higher values reduce similarity to the reference.
- **start_at / end_at**: Control when IP-Adapter influence is active during sampling. `start_at=0.0, end_at=0.8` applies IP-Adapter for the first 80% of steps, letting the model refine independently at the end.
- **CLIP Vision model must match**: The CLIP vision model must be compatible with the IP-Adapter weights. SDXL IP-Adapter uses ViT-H or ViT-bigG; SD1.5 uses ViT-H or ViT-L.
- **Text vs image**: IP-Adapter and text prompt compete for influence. If IP-Adapter weight is high, text prompt may be partially ignored. Balance both.
- **Resolution**: Reference images are internally resized by CLIP vision. Input resolution doesn't critically matter, but clean, high-quality references produce better features.
- **Style transfer**: Use style-focused IP-Adapter models (e.g., `ip-adapter-plus-face_sdxl_vit-h` for faces, `ip-adapter-plus_sdxl_vit-h` for general style).
- **Composition**: IP-Adapter transfers composition and layout from the reference. Adjust `weight` to control how closely the output follows the reference layout.

## Example Widget Values

### Style Transfer

```
CheckpointLoaderSimple: ckpt_name = "sd_xl_base_1.0.safetensors"
CLIPVisionLoader: clip_name = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
IPAdapterModelLoader: ipadapter_file = "ip-adapter-plus_sdxl_vit-h.safetensors"
LoadImage: image = "starry_night_crop.png"
IPAdapterApply: weight=0.7, weight_type="original", start_at=0.0, end_at=1.0, noise=0.0
CLIPTextEncode: text = "a modern cityscape, oil painting style"
KSampler: seed=42, steps=30, cfg=7.0
```

### Character Consistency

```
IPAdapterModelLoader: ipadapter_file = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
LoadImage: image = "character_reference.png"
IPAdapterApply: weight=0.9, weight_type="original", start_at=0.0, end_at=0.9
CLIPTextEncode: text = "the character standing in a forest, detailed face"
```

### Composition Guidance

```
LoadImage: image = "composition_ref.png"
IPAdapterApply: weight=0.5, weight_type="linear", start_at=0.0, end_at=0.6
CLIPTextEncode: text = "a completely different subject in the same layout"
```
