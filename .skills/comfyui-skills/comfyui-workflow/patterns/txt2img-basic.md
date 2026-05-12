# txt2img-basic

Basic text-to-image generation pipeline.

## When to Use

- Generating images from text prompts
- Starting point for most workflows
- Testing models, prompts, and settings

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Loads the diffusion model, CLIP, and VAE |
| `CLIPTextEncode` (positive) | Encodes the positive prompt |
| `CLIPTextEncode` (negative) | Encodes the negative prompt |
| `EmptyLatentImage` | Creates a blank latent at target resolution |
| `KSampler` | Runs the diffusion sampling process |
| `VAEDecode` | Decodes latent to pixel image |
| `SaveImage` | Saves the output to disk |

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple

- **Outputs:** `MODEL`, `CLIP`, `VAE`
- **Widget:** `ckpt_name` — model filename, e.g. `"v1-5-pruned-emaonly.safetensors"`

### 2. CLIPTextEncode (positive)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — positive prompt, e.g. `"a photo of a cat sitting on a windowsill, natural light"`
- **Output:** `CONDITIONING`

### 3. CLIPTextEncode (negative)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — negative prompt, e.g. `"blurry, low quality, deformed"`
- **Output:** `CONDITIONING`

### 4. EmptyLatentImage

- **Widgets:**
  - `width` — e.g. `512`
  - `height` — e.g. `512`
  - `batch_size` — e.g. `1`
- **Output:** `LATENT`

### 5. KSampler

- **Inputs:**
  - `model` ← from CheckpointLoaderSimple
  - `positive` ← from CLIPTextEncode (positive)
  - `negative` ← from CLIPTextEncode (negative)
  - `latent_image` ← from EmptyLatentImage
- **Widgets:**
  - `seed` — e.g. `42`
  - `steps` — e.g. `20`
  - `cfg` — e.g. `7.0`
  - `sampler_name` — e.g. `"euler"`
  - `scheduler` — e.g. `"normal"`
  - `denoise` — `1.0` (full generation)
- **Output:** `LATENT`

### 6. VAEDecode

- **Inputs:**
  - `samples` ← from KSampler
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `IMAGE`

### 7. SaveImage

- **Input:** `images` ← from VAEDecode
- **Widget:** `filename_prefix` — e.g. `"output"`

## Connection Order

```
CheckpointLoaderSimple ─┬─ MODEL ──────────────► KSampler
                        ├─ CLIP ──┬────────────► CLIPTextEncode (positive)
                        │         └────────────► CLIPTextEncode (negative)
                        └─ VAE ─────────────────► VAEDecode

CLIPTextEncode (pos) ───── CONDITIONING ────────► KSampler [positive]
CLIPTextEncode (neg) ───── CONDITIONING ────────► KSampler [negative]
EmptyLatentImage ────────── LATENT ─────────────► KSampler [latent_image]

KSampler ────────────────── LATENT ─────────────► VAEDecode [samples]
VAEDecode ───────────────── IMAGE ──────────────► SaveImage
```

## Key Considerations

- **Resolution:** Use 512x512 for SD 1.5, 1024x1024 for SDXL
- **CFG scale:** 5-8 is typical; higher values enforce prompt adherence more strongly
- **Steps:** 20-30 is standard; more steps = slower but potentially cleaner
- **Sampler:** `euler` is fast, `dpmpp_2m` is high quality, `ddim` is deterministic
- **Denoise:** Must be `1.0` for txt2img (no input image to denoise from)
