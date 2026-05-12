# sdxl-refiner

SDXL base + refiner two-stage sampling pipeline.

## When to Use

- Generating high-quality SDXL images with refined details
- When you want the base model for composition and the refiner for detail/texture
- Production-quality outputs where quality matters more than speed

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` (base) | Loads the SDXL base model |
| `CheckpointLoaderSimple` (refiner) | Loads the SDXL refiner model |
| `CLIPTextEncode` (positive, base) | Encodes positive prompt for base |
| `CLIPTextEncode` (negative, base) | Encodes negative prompt for base |
| `EmptyLatentImage` | Creates blank latent at SDXL resolution |
| `KSampler` (base) | Runs base sampling (rough composition) |
| `KSampler` (refiner) | Runs refiner sampling (detail pass) |
| `VAEDecode` | Decodes final latent to image |
| `SaveImage` | Saves output |

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple (base)

- **Widget:** `ckpt_name` — e.g. `"sd_xl_base_1.0.safetensors"`
- **Outputs:** `MODEL`, `CLIP`, `VAE`

### 2. CheckpointLoaderSimple (refiner)

- **Widget:** `ckpt_name` — e.g. `"sd_xl_refiner_1.0.safetensors"`
- **Outputs:** `MODEL`, `CLIP`, `VAE`

### 3. CLIPTextEncode (positive)

- **Input:** `CLIP` ← from CheckpointLoaderSimple (base)
- **Widget:** `text` — e.g. `"a majestic lion on a rocky cliff at sunset, 8k, highly detailed"`
- **Output:** `CONDITIONING`

### 4. CLIPTextEncode (negative)

- **Input:** `CLIP` ← from CheckpointLoaderSimple (base)
- **Widget:** `text` — e.g. `"blurry, low quality, deformed"`
- **Output:** `CONDITIONING`

### 5. EmptyLatentImage

- **Widgets:**
  - `width` — `1024`
  - `height` — `1024`
  - `batch_size` — `1`
- **Output:** `LATENT`

### 6. KSampler (base)

- **Inputs:**
  - `model` ← from CheckpointLoaderSimple (base)
  - `positive` ← from CLIPTextEncode (positive)
  - `negative` ← from CLIPTextEncode (negative)
  - `latent_image` ← from EmptyLatentImage
- **Widgets:**
  - `seed` — e.g. `42`
  - `steps` — e.g. `30` (total steps for the full pipeline)
  - `cfg` — e.g. `7.0`
  - `sampler_name` — e.g. `"euler_ancestral"`
  - `scheduler` — e.g. `"normal"`
  - `denoise` — `1.0`
  - **`start_at_step` — `0`** (start from the beginning)
  - **`end_at_step` — `20`** (stop at step 20, hand off to refiner)
- **Output:** `LATENT`

### 7. KSampler (refiner)

- **Inputs:**
  - `model` ← from CheckpointLoaderSimple (refiner)
  - `positive` ← from CLIPTextEncode (positive)
  - `negative` ← from CLIPTextEncode (negative)
  - `latent_image` ← from KSampler (base) output
- **Widgets:**
  - `seed` — same as base for consistency
  - `steps` — e.g. `30` (same total step count)
  - `cfg` — e.g. `7.0`
  - `sampler_name` — e.g. `"euler_ancestral"`
  - `scheduler` — e.g. `"normal"`
  - `denoise` — `1.0`
  - **`start_at_step` — `20`** (continue from where base stopped)
  - **`end_at_step` — `30`** (finish the remaining steps)
- **Output:** `LATENT`

### 8. VAEDecode

- **Inputs:**
  - `samples` ← from KSampler (refiner)
  - `vae` ← from CheckpointLoaderSimple (refiner) **or** (base) — both work, refiner VAE is typical
- **Output:** `IMAGE`

### 9. SaveImage

- **Input:** `images` ← from VAEDecode
- **Widget:** `filename_prefix` — e.g. `"sdxl_output"`

## Connection Order

```
CheckpointLoaderSimple (base) ─┬─ MODEL ─────────────────────► KSampler (base)
                               ├─ CLIP ──┬───────────────────► CLIPTextEncode (pos)
                               │         └───────────────────► CLIPTextEncode (neg)
                               └─ VAE ───────────────────────► VAEDecode (optional)

CheckpointLoaderSimple (ref) ─── MODEL ──────────────────────► KSampler (refiner)
                                 VAE ────────────────────────► VAEDecode (typical)

CLIPTextEncode (pos) ─────────── CONDITIONING ─┬─────────────► KSampler (base) [positive]
                                                └─────────────► KSampler (refiner) [positive]
CLIPTextEncode (neg) ─────────── CONDITIONING ─┬─────────────► KSampler (base) [negative]
                                                └─────────────► KSampler (refiner) [negative]

EmptyLatentImage ──────────────── LATENT ─────────────────────► KSampler (base) [latent_image]

KSampler (base) ───────────────── LATENT ─────────────────────► KSampler (refiner) [latent_image]
KSampler (refiner) ────────────── LATENT ─────────────────────► VAEDecode [samples]
VAEDecode ──────────────────────── IMAGE ──────────────────────► SaveImage
```

## Key Considerations

- **Step math:** `end_at_step` of base + `start_at_step` of refiner must be equal. `steps` must be the same value in both samplers. Common split: 20/30 (base does 20 steps, refiner does 10).
- **Resolution:** SDXL native resolution is 1024x1024. Use resolutions like 1024x1024, 1152x896, 896x1152, 1216x832, etc.
- **CFG values:** Both samplers typically use the same CFG (7.0). The refiner can tolerate slightly lower CFG.
- **Same seed:** Use the same seed in both samplers for deterministic results.
- **Base-only mode:** You can skip the refiner by setting `end_at_step` equal to `steps` in the base sampler.
- **Prompt:** The same prompt is used for both base and refiner. The base interprets it for composition; the refiner uses it for detail.
- **VAE:** The refiner's VAE is typically used for decoding, but either works.
