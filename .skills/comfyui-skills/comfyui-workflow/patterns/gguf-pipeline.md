# GGUF Quantized Model Pipeline

## When to Use

Run large diffusion models on GPUs with limited VRAM (8-12GB instead of 24GB+). Use GGUF quantized models when full-precision models exceed your available memory. GGUF uses lossy compression — quality is lower than full precision but the tradeoff is acceptable for most use cases, especially for preview and iterative work.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Load GGUF checkpoint (same node as full precision) |
| `CLIPTextEncode` | Encode text prompt |
| `EmptyLatentImage` | Create blank latent |
| `KSampler` | Denoise latent |
| `VAEDecode` | Decode latent to pixel image |
| `SaveImage` | Save final output |

## Connection Order

The pipeline structure is identical to a standard workflow. The only difference is the model file loaded:

```
CheckpointLoaderSimple
  ├── MODEL → KSampler.model
  ├── CLIP  → CLIPTextEncode.clip
  └── VAE   → VAEDecode.vae

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

## GGUF Quantization Details

### What is GGUF

GGUF (GGML Unified Format) is a quantized model format that reduces model size and VRAM usage through lossy compression. Originally designed for LLM inference, adapted for diffusion models.

### Quantization Levels

| Quantization | Size Reduction | Quality | VRAM (SDXL) |
|---|---|---|---|
| Q4_0 | ~75% | Noticeable degradation | ~6GB |
| Q4_K_M | ~70% | Good balance | ~7GB |
| Q5_K_M | ~60% | Near original | ~8GB |
| Q6_K | ~50% | Very close to original | ~10GB |
| Q8_0 | ~25% | Minimal difference | ~12GB |
| Full (FP16) | 0% | Reference | ~24GB |

### When to Use Each Level

- **Q4_0/Q4_K_M**: Maximum VRAM savings, acceptable for previews and testing
- **Q5_K_M**: Best balance of quality and size for most workflows
- **Q6_K**: Near-original quality with meaningful savings
- **Q8_0**: Minimal savings, use only if FP16 barely doesn't fit
- **FP16**: Full quality, requires 24GB+ VRAM

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple (GGUF)

```
Inputs:
  ckpt_name: "sdxl_base_v1.0-Q5_K_M.gguf"        (widget, GGUF file)

Outputs:
  MODEL → KSampler.model
  CLIP  → CLIPTextEncode.clip
  VAE   → VAEDecode.vae
```

### 2. CLIPTextEncode (positive)

```
Inputs:
  text: "a highly detailed photograph of a mountain landscape"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → KSampler.positive
```

### 3. CLIPTextEncode (negative)

```
Inputs:
  text: "blurry, low quality, distorted"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → KSampler.negative
```

### 4. EmptyLatentImage

```
Inputs:
  width:      1024                                 (widget, int)
  height:     1024                                 (widget, int)
  batch_size: 1                                    (widget, int)

Outputs:
  LATENT → KSampler.latent_image
```

### 5. KSampler

```
Inputs:
  model:        ← CheckpointLoaderSimple.MODEL
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

### 6. VAEDecode

```
Inputs:
  samples: ← KSampler.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → SaveImage.images
```

### 7. SaveImage

```
Inputs:
  images: ← VAEDecode.IMAGE
  filename_prefix: "gguf_output"
```

## Key Considerations

- **Same pipeline**: GGUF models use the exact same node graph as full-precision models. No special nodes required — just load a `.gguf` file instead of `.safetensors`.
- **Quality loss**: Quantization introduces noise and reduces fine detail. Q5_K_M is the minimum recommended for production work.
- **Speed**: GGUF inference is slightly slower than FP16 due to dequantization overhead during forward passes.
- **VAE separate**: GGUF checkpoints may not include a VAE. You may need to load a separate VAE using `VAELoader` if the checkpoint's VAE output is missing or poor quality.
- **Compatibility**: Not all model architectures support GGUF. SDXL, SD1.5, and Flux have GGUF support. Newer architectures may require updated quantization tools.
- **File size**: A Q5_K_M SDXL checkpoint is ~7GB vs ~7GB for FP16 (SDXL is already relatively compact). The savings are more dramatic for larger models like Flux (~24GB FP16 → ~10GB Q5_K_M).
- **Batch size**: With reduced VRAM, you can often increase batch size. Test to find the optimal balance.
- **LoRA compatibility**: LoRA adapters trained on full-precision models work with GGUF models but may produce slightly different results due to the quantized base weights.
- **Upscaling**: For final output, consider using GGUF for generation and full-precision for upscaling/refinement passes.
- **Model sources**: GGUF conversions are available on HuggingFace and CivitAI. Look for community-converted files or use conversion tools.

## Example Widget Values

### Standard GGUF Workflow

```
CheckpointLoaderSimple: ckpt_name = "sdxl_base_v1.0-Q5_K_M.gguf"
CLIPTextEncode: text = "a highly detailed photograph of a mountain landscape"
EmptyLatentImage: width=1024, height=1024, batch_size=1
KSampler: seed=42, steps=30, cfg=7.0, sampler_name="dpmpp_2m", scheduler="karras"
```

### GGUF with Separate VAE

```
CheckpointLoaderSimple: ckpt_name = "flux1-dev-Q5_K_M.gguf"
VAELoader: vae_name = "ae.safetensors"
KSampler: seed=42, steps=20, cfg=3.5, sampler_name="euler", scheduler="normal"
```

### GGUF for Video (LTXV)

```
CheckpointLoaderSimple: ckpt_name = "ltxv-13b-Q6_K.gguf"
EmptyLTXVLatentVideo: width=480, height=256, frame_count=97
KSampler: seed=42, steps=25, cfg=7.0
```
