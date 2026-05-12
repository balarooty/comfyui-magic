# inpaint

Inpainting pipeline for selective area regeneration.

## When to Use

- Replacing or regenerating specific areas of an image
- Fixing defects, removing objects, or adding new content to a region
- When you have a mask defining the area to modify

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Loads model, CLIP, and VAE |
| `CLIPTextEncode` (positive) | Encodes positive prompt |
| `CLIPTextEncode` (negative) | Encodes negative prompt |
| `LoadImage` | Loads the source image |
| `LoadImage` (mask) or `ImageToMask` | Provides the inpainting mask |
| `VAEEncode` | Encodes source image to latent |
| `SetLatentNoiseMask` | Applies the mask to the latent |
| `KSampler` | Samples only within the masked area |
| `VAEDecode` | Decodes latent to image |
| `SaveImage` | Saves output |

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple

- **Outputs:** `MODEL`, `CLIP`, `VAE`
- **Widget:** `ckpt_name` — e.g. `"v1-5-pruned-emaonly.safetensors"` (or an inpainting-specific model)

### 2. CLIPTextEncode (positive)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — describe what should appear in the masked area, e.g. `"a red sports car"`
- **Output:** `CONDITIONING`

### 3. CLIPTextEncode (negative)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — e.g. `"blurry, low quality, artifacts"`
- **Output:** `CONDITIONING`

### 4. LoadImage (source image)

- **Widget:** `image` — e.g. `"source_photo.png"`
- **Output:** `IMAGE`, `MASK`

### 5. ImageToMask (or use LoadImage MASK output directly)

- **Input:** `image` ← from LoadImage (if using a separate mask image) or use the `MASK` output directly from LoadImage
- **Widget:** `channel` — `"red"`, `"green"`, `"blue"`, or `"alpha"` (use the channel where the mask is defined)
- **Output:** `MASK`

> **Note:** If the mask is a separate grayscale image, load it with a second `LoadImage` node and connect its output to an `ImageToMask` node. If using the alpha channel or a built-in mask from LoadImage, connect `MASK` directly.

### 6. VAEEncode

- **Inputs:**
  - `pixels` ← from LoadImage (source)
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `LATENT`

### 7. SetLatentNoiseMask

- **Inputs:**
  - `samples` ← from VAEEncode
  - `mask` ← from ImageToMask or LoadImage (MASK output)
- **Output:** `LATENT` (with mask applied)

### 8. KSampler

- **Inputs:**
  - `model` ← from CheckpointLoaderSimple
  - `positive` ← from CLIPTextEncode (positive)
  - `negative` ← from CLIPTextEncode (negative)
  - `latent_image` ← from SetLatentNoiseMask
- **Widgets:**
  - `seed` — e.g. `42`
  - `steps` — e.g. `20`
  - `cfg` — e.g. `7.0`
  - `sampler_name` — e.g. `"euler"`
  - `scheduler` — e.g. `"normal"`
  - `denoise` — e.g. `1.0` (for full regeneration of masked area)
- **Output:** `LATENT`

### 9. VAEDecode

- **Inputs:**
  - `samples` ← from KSampler
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `IMAGE`

### 10. SaveImage

- **Input:** `images` ← from VAEDecode
- **Widget:** `filename_prefix` — e.g. `"inpaint_output"`

## Connection Order

```
CheckpointLoaderSimple ─┬─ MODEL ──────────────► KSampler
                        ├─ CLIP ──┬────────────► CLIPTextEncode (pos)
                        │         └────────────► CLIPTextEncode (neg)
                        └─ VAE ──┬────────────► VAEEncode
                                 └────────────► VAEDecode

LoadImage (source) ──────┬─ IMAGE ─────────────► VAEEncode [pixels]
                         └─ MASK ──────────────► SetLatentNoiseMask [mask]
                            (or via ImageToMask)

CLIPTextEncode (pos) ───── CONDITIONING ────────► KSampler [positive]
CLIPTextEncode (neg) ───── CONDITIONING ────────► KSampler [negative]

VAEEncode ───────────────── LATENT ─────────────► SetLatentNoiseMask [samples]
SetLatentNoiseMask ──────── LATENT ─────────────► KSampler [latent_image]

KSampler ────────────────── LATENT ─────────────► VAEDecode [samples]
VAEDecode ───────────────── IMAGE ──────────────► SaveImage
```

## Key Considerations

- **Mask is white = area to regenerate, black = preserve.** Ensure your mask follows this convention.
- **Denoise:** Use `1.0` to fully regenerate the masked area. Lower values (0.5-0.8) will blend the new content with the original, which can be useful for subtle modifications.
- **Inpainting-specific models:** Models fine-tuned for inpainting (e.g. `v1-5-inpainting.safetensors`) produce better results at mask boundaries because they were trained with masked inputs.
- **Mask feathering:** Hard mask edges can cause visible seams. Consider using a slightly blurred/feathered mask for smoother blending.
- **Prompt scope:** Describe what should appear in the masked area, not the entire image.
- **CFG and steps:** Standard values (CFG 7.0, 20 steps) work well for inpainting.
- **Resolution:** The source image should be at a standard resolution (512x512 for SD 1.5). Resize before processing if needed.
