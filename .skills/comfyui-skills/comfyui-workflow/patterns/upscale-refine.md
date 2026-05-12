# upscale-refine

Multi-pass upscale and refine pipeline for high-resolution output.

## When to Use

- Generating images larger than the model's native resolution
- When you want high-resolution output with fine details
- Production workflows requiring 2x-4x upscaling with quality preservation

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Loads model, CLIP, and VAE |
| `CLIPTextEncode` (positive) | Encodes positive prompt |
| `CLIPTextEncode` (negative) | Encodes negative prompt |
| `EmptyLatentImage` | Creates initial low-res latent |
| `KSampler` (pass 1) | Generates low-res base image |
| `VAEDecode` (pass 1) | Decodes low-res latent to image |
| `UpscaleModelLoader` | Loads an upscale model (e.g. RealESRGAN) |
| `ImageUpscaleWithModel` | Upscales the image using the loaded model |
| `VAEEncode` | Re-encodes the upscaled image to latent |
| `KSampler` (pass 2) | Refines the upscaled latent with low denoise |
| `VAEDecode` (pass 2) | Decodes the refined latent to final image |
| `SaveImage` | Saves the final high-res output |

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple

- **Outputs:** `MODEL`, `CLIP`, `VAE`
- **Widget:** `ckpt_name` — e.g. `"v1-5-pruned-emaonly.safetensors"`

### 2. CLIPTextEncode (positive)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — e.g. `"a detailed landscape painting, mountains, lake, 8k"`
- **Output:** `CONDITIONING`

### 3. CLIPTextEncode (negative)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — e.g. `"blurry, low quality, artifacts, noise"`
- **Output:** `CONDITIONING`

### 4. EmptyLatentImage (low-res)

- **Widgets:**
  - `width` — e.g. `512`
  - `height` — e.g. `512`
  - `batch_size` — `1`
- **Output:** `LATENT`

### 5. KSampler (pass 1 — base generation)

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
  - `denoise` — `1.0`
- **Output:** `LATENT`

### 6. VAEDecode (pass 1)

- **Inputs:**
  - `samples` ← from KSampler (pass 1)
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `IMAGE`

### 7. UpscaleModelLoader

- **Widget:** `model_name` — e.g. `"RealESRGAN_x4plus.pth"` or `"4x-UltraSharp.pth"`
- **Output:** `UPSCALE_MODEL`

### 8. ImageUpscaleWithModel

- **Inputs:**
  - `upscale_model` ← from UpscaleModelLoader
  - `image` ← from VAEDecode (pass 1)
- **Output:** `IMAGE` (upscaled, e.g. 512→2048 with 4x model)

### 9. VAEEncode (re-encode upscaled image)

- **Inputs:**
  - `pixels` ← from ImageUpscaleWithModel
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `LATENT`

### 10. KSampler (pass 2 — refine)

- **Inputs:**
  - `model` ← from CheckpointLoaderSimple
  - `positive` ← from CLIPTextEncode (positive)
  - `negative` ← from CLIPTextEncode (negative)
  - `latent_image` ← from VAEEncode (upscaled)
- **Widgets:**
  - `seed` — same as pass 1 for consistency
  - `steps` — e.g. `20`
  - `cfg` — e.g. `7.0`
  - `sampler_name` — e.g. `"euler"`
  - `scheduler` — e.g. `"normal"`
  - `denoise` — **`0.3` to `0.5`** (critical: low denoise preserves composition)
- **Output:** `LATENT`

### 11. VAEDecode (pass 2)

- **Inputs:**
  - `samples` ← from KSampler (pass 2)
  - `vae` ← from CheckpointLoaderSimple
- **Output:** `IMAGE`

### 12. SaveImage

- **Input:** `images` ← from VAEDecode (pass 2)
- **Widget:** `filename_prefix` — e.g. `"upscaled_output"`

## Connection Order

```
CheckpointLoaderSimple ─┬─ MODEL ──────────────────────────────────────► KSampler (pass 1)
                        │                                             ► KSampler (pass 2)
                        ├─ CLIP ──┬──────────────────────────────────► CLIPTextEncode (pos)
                        │         └──────────────────────────────────► CLIPTextEncode (neg)
                        └─ VAE ──┬──────────────────────────────────► VAEDecode (pass 1)
                                 ├──────────────────────────────────► VAEEncode
                                 └──────────────────────────────────► VAEDecode (pass 2)

EmptyLatentImage ──────── LATENT ────────────────────────────────────► KSampler (pass 1) [latent_image]

CLIPTextEncode (pos) ──── CONDITIONING ─┬────────────────────────────► KSampler (pass 1) [positive]
                                        └────────────────────────────► KSampler (pass 2) [positive]
CLIPTextEncode (neg) ──── CONDITIONING ─┬────────────────────────────► KSampler (pass 1) [negative]
                                        └────────────────────────────► KSampler (pass 2) [negative]

KSampler (pass 1) ─────── LATENT ────────────────────────────────────► VAEDecode (pass 1) [samples]
VAEDecode (pass 1) ────── IMAGE ─────────────────────────────────────► ImageUpscaleWithModel [image]

UpscaleModelLoader ─────── UPSCALE_MODEL ────────────────────────────► ImageUpscaleWithModel [upscale_model]

ImageUpscaleWithModel ──── IMAGE ────────────────────────────────────► VAEEncode [pixels]
VAEEncode ──────────────── LATENT ────────────────────────────────────► KSampler (pass 2) [latent_image]

KSampler (pass 2) ─────── LATENT ────────────────────────────────────► VAEDecode (pass 2) [samples]
VAEDecode (pass 2) ────── IMAGE ─────────────────────────────────────► SaveImage
```

## Key Considerations

- **Pass 2 denoise is the critical parameter:**
  - `0.3` — subtle refinement, adds minor detail, very safe
  - `0.4` — balanced, adds noticeable detail and texture
  - `0.5` — stronger refinement, may shift colors/composition slightly
  - `> 0.6` — risky, can significantly alter the image
- **Upscale model choice:** RealESRGAN and similar models add sharpness and detail during upscaling. The diffusion refine pass then adds coherent texture. Both steps are important.
- **Resolution math:** With a 4x upscale model, 512x512 → 2048x2048. The refine pass operates at the upscaled resolution, which requires significant VRAM. Consider 2x models for large base resolutions.
- **Same prompt:** Use the same prompt for both passes. The refine pass uses the prompt to add contextually appropriate details.
- **Same seed:** Using the same seed in both passes helps maintain consistency.
- **Alternative approach — latent upscale:** Instead of `ImageUpscaleWithModel` + `VAEEncode`, you can use `LatentUpscale` to upscale directly in latent space (faster but lower quality).
- **Tiling for VRAM:** For very high resolutions, consider using tiled VAE decode/encode or tiled KSampler to reduce VRAM requirements.
