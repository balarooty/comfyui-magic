# img2img

Image-to-image transformation pipeline.

## When to Use

- Transforming an existing image with a prompt (style transfer, modifications)
- Refining or altering a previously generated image
- When you have a reference image to guide composition

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Loads model, CLIP, and VAE |
| `CLIPTextEncode` (positive) | Encodes the positive prompt |
| `CLIPTextEncode` (negative) | Encodes the negative prompt |
| `LoadImage` | Loads the source image |
| `VAEEncode` | Encodes the source image into latent space |
| `KSampler` | Runs diffusion with denoise < 1.0 |
| `VAEDecode` | Decodes latent back to image |
| `SaveImage` | Saves the output |

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple

- **Outputs:** `MODEL`, `CLIP`, `VAE`
- **Widget:** `ckpt_name` — e.g. `"v1-5-pruned-emaonly.safetensors"`

### 2. CLIPTextEncode (positive)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — e.g. `"a painting of a cat in impressionist style"`
- **Output:** `CONDITIONING`

### 3. CLIPTextEncode (negative)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — e.g. `"blurry, low quality"`
- **Output:** `CONDITIONING`

### 4. LoadImage

- **Widget:** `image` — filename in input folder, e.g. `"source.png"`
- **Output:** `IMAGE`, `MASK`

### 5. VAEEncode

- **Inputs:**
  - `pixels` ← from LoadImage
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `LATENT`

### 6. KSampler

- **Inputs:**
  - `model` ← from CheckpointLoaderSimple
  - `positive` ← from CLIPTextEncode (positive)
  - `negative` ← from CLIPTextEncode (negative)
  - `latent_image` ← from VAEEncode
- **Widgets:**
  - `seed` — e.g. `42`
  - `steps` — e.g. `20`
  - `cfg` — e.g. `7.0`
  - `sampler_name` — e.g. `"euler"`
  - `scheduler` — e.g. `"normal"`
  - `denoise` — **< 1.0** (critical for img2img)
- **Output:** `LATENT`

### 7. VAEDecode

- **Inputs:**
  - `samples` ← from KSampler
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `IMAGE`

### 8. SaveImage

- **Input:** `images` ← from VAEDecode
- **Widget:** `filename_prefix` — e.g. `"img2img_output"`

## Connection Order

```
CheckpointLoaderSimple ─┬─ MODEL ──────────────► KSampler
                        ├─ CLIP ──┬────────────► CLIPTextEncode (positive)
                        │         └────────────► CLIPTextEncode (negative)
                        └─ VAE ──┬────────────► VAEEncode
                                 └────────────► VAEDecode

LoadImage ───────────────── IMAGE ─────────────► VAEEncode [pixels]

CLIPTextEncode (pos) ───── CONDITIONING ────────► KSampler [positive]
CLIPTextEncode (neg) ───── CONDITIONING ────────► KSampler [negative]
VAEEncode ───────────────── LATENT ─────────────► KSampler [latent_image]

KSampler ────────────────── LATENT ─────────────► VAEDecode [samples]
VAEDecode ───────────────── IMAGE ──────────────► SaveImage
```

## Key Considerations

- **Denoise strength is the critical parameter:**
  - `0.3` — minor changes, preserves composition and details closely
  - `0.5` — balanced transformation, keeps general structure
  - `0.7` — major changes, only broad strokes remain
  - `1.0` — equivalent to txt2img (ignores source image entirely)
- **Resolution matters:** Resize source image to a standard resolution (512x512 for SD 1.5, 1024x1024 for SDXL) before encoding
- **Prompt alignment:** The prompt should describe the desired output, not the input
- **VAE encoding:** The source image must be encoded through the same VAE used by the model
