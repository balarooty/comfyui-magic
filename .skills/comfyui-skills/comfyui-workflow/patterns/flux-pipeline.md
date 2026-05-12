# flux-pipeline

Flux model pipeline using Flux-specific loaders and sampler architecture.

## When to Use

- Running Flux models (FLUX.1 dev, FLUX.1 schnell, etc.)
- When you need Flux's prompt adherence and quality
- Flux uses a fundamentally different architecture from SD 1.5/SDXL

## Required Nodes

| Node Type | Purpose |
|---|---|
| `UNETLoader` | Loads the Flux UNET model |
| `DualCLIPLoader` | Loads both CLIP encoders (clip_l + t5xxl) |
| `VAELoader` | Loads the Flux VAE |
| `CLIPTextEncodeFlux` | Flux-specific text encoder (handles dual CLIP) |
| `EmptyLatentImage` | Creates blank latent |
| `BasicGuider` | Creates a basic guider from model + conditioning |
| `CFGGuider` | Creates a CFG-based guider (alternative to BasicGuider) |
| `BasicScheduler` | Defines the noise schedule |
| `KSamplerSelect` | Selects the sampler algorithm |
| `SamplerCustom` | Runs the custom sampling process |
| `VAEDecode` | Decodes latent to image |
| `SaveImage` | Saves output |

## Node-by-Node Wiring Guide

### 1. UNETLoader

- **Widgets:**
  - `unet_name` — e.g. `"flux1-dev.safetensors"`
  - `weight_dtype` — e.g. `"default"` or `"fp8_e4m3fn"` for lower VRAM
- **Output:** `MODEL`

### 2. DualCLIPLoader

- **Widgets:**
  - `clip_name1` — e.g. `"t5xxl_fp16.safetensors"` (T5 encoder)
  - `clip_name2` — e.g. `"clip_l.safetensors"` (CLIP-L encoder)
  - `type` — `"flux"` (determines clip type handling)
- **Output:** `CLIP`

### 3. VAELoader

- **Widget:** `vae_name` — e.g. `"ae.safetensors"` (Flux VAE)
- **Output:** `VAE`

### 4. CLIPTextEncodeFlux

- **Input:** `clip` ← from DualCLIPLoader
- **Widgets:**
  - `text` — prompt, e.g. `"a photorealistic cat wearing sunglasses, studio lighting"`
  - `guidance` — e.g. `3.5` (Flux-specific guidance value; controls prompt adherence)
- **Output:** `CONDITIONING`

### 5. EmptyLatentImage

- **Widgets:**
  - `width` — e.g. `1024`
  - `height` — e.g. `1024`
  - `batch_size` — e.g. `1`
- **Output:** `LATENT`

### 6. BasicGuider (or CFGGuider)

**Option A: BasicGuider** (common for Flux dev)

- **Inputs:**
  - `model` ← from UNETLoader
  - `cond` ← from CLIPTextEncodeFlux
- **Output:** `GUIDER`

**Option B: CFGGuider** (for CFG-based sampling)

- **Inputs:**
  - `model` ← from UNETLoader
  - `positive` ← from CLIPTextEncodeFlux
  - `negative` ← from CLIPTextEncodeFlux (can use empty or a negative prompt)
- **Widgets:**
  - `cfg` — e.g. `1.0` (Flux often uses low or no CFG)
- **Output:** `GUIDER`

### 7. BasicScheduler

- **Inputs:**
  - `model` ← from UNETLoader
- **Widgets:**
  - `scheduler` — e.g. `"normal"` or `"simple"`
  - `steps` — e.g. `20` (Flux dev), `4` (Flux schnell)
  - `denoise` — `1.0`
- **Output:** `SIGMAS`

### 8. KSamplerSelect

- **Widget:** `sampler_name` — e.g. `"euler"` or `"heun"`
- **Output:** `SAMPLER`

### 9. SamplerCustom

- **Inputs:**
  - `model` ← from UNETLoader
  - `guider` ← from BasicGuider or CFGGuider
  - `sigmas` ← from BasicScheduler
  - `latent_image` ← from EmptyLatentImage
  - `sampler` ← from KSamplerSelect
- **Output:** `LATENT`, `LATENT` (denoised output, denoised output)

### 10. VAEDecode

- **Inputs:**
  - `samples` ← from SamplerCustom (first output)
  - `vae` ← from VAELoader
- **Output:** `IMAGE`

### 11. SaveImage

- **Input:** `images` ← from VAEDecode
- **Widget:** `filename_prefix` — e.g. `"flux_output"`

## Connection Order

```
UNETLoader ──────────────┬─ MODEL ──────────────► BasicGuider [model]
                         │                     ► BasicScheduler [model]
                         │                     ► SamplerCustom [model]
                         │
DualCLIPLoader ── CLIP ──┼─► CLIPTextEncodeFlux [clip]
                         │
VAELoader ────── VAE ───────────────────────────► VAEDecode [vae]

CLIPTextEncodeFlux ──────── CONDITIONING ────────► BasicGuider [cond]

BasicGuider ─────────────── GUIDER ──────────────► SamplerCustom [guider]
BasicScheduler ──────────── SIGMAS ──────────────► SamplerCustom [sigmas]
KSamplerSelect ──────────── SAMPLER ─────────────► SamplerCustom [sampler]
EmptyLatentImage ─────────── LATENT ─────────────► SamplerCustom [latent_image]

SamplerCustom ────────────── LATENT ─────────────► VAEDecode [samples]
VAEDecode ────────────────── IMAGE ──────────────► SaveImage
```

## Key Considerations

- **No negative prompt by default:** Flux uses `CLIPTextEncodeFlux` with a single prompt and a `guidance` value, not separate positive/negative conditioning. If using CFGGuider, you can add a negative, but it's uncommon.
- **Guidance value:** The `guidance` parameter in `CLIPTextEncodeFlux` is Flux-specific. Typical range: 3.0-4.0 for dev, lower for schnell.
- **Different sampler architecture:** Flux uses `SamplerCustom` + `BasicGuider`/`CFGGuider` + `BasicScheduler` + `KSamplerSelect` instead of the standard `KSampler` node.
- **Dual CLIP:** Flux requires two text encoders loaded via `DualCLIPLoader` — CLIP-L and T5-XXL.
- **Separate VAE:** The Flux VAE is loaded independently via `VAELoader`, not bundled with the checkpoint.
- **Flux dev vs. schnell:** Dev requires more steps (20+) and uses guidance; schnell is fast (4 steps) and may not need guidance.
- **VRAM:** Flux models are large. Use `weight_dtype="fp8_e4m3fn"` in UNETLoader to reduce VRAM usage.
- **Resolution:** Flux works well at 1024x1024 and various aspect ratios.
