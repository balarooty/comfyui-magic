# Custom Model Patching Patterns

## When to Use

Modify a diffusion model's internal behavior at runtime — custom attention mechanisms, alternative sampling strategies, cross-attention injection, or monkey-patching forward methods. Use when standard nodes cannot express the desired modification, and you need direct control over the model's computation graph.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `CheckpointLoaderSimple` | Load base diffusion model |
| `ModelPatchNode` | Custom node that patches the model (node name varies) |
| `CLIPTextEncode` | Encode text prompt |
| `EmptyLatentImage` | Create blank latent |
| `KSampler` | Denoise latent using patched model |
| `VAEDecode` | Decode latent to pixel image |
| `SaveImage` | Save final output |

## Connection Order

```
CheckpointLoaderSimple
  ├── model → ModelPatchNode.model
  ├── clip  → CLIPTextEncode.clip
  └── vae   → VAEDecode.vae

ModelPatchNode
  └── MODEL → KSampler.model

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
  MODEL → ModelPatchNode.model
  CLIP  → CLIPTextEncode.clip
  VAE   → VAEDecode.vae
```

### 2. ModelPatchNode

Custom node that modifies the model. The exact node name depends on the custom node pack. Common examples:

- `ModelPatchAttnKVBias` — modify attention key/value
- `PatchModelAddDownscale` — add downscale to model
- `ModelMergeSimple` — merge two models
- Custom Python node using `model.clone()` and `model_options`

```
Inputs:
  model:      ← CheckpointLoaderSimple.MODEL
  strength:   1.0                                  (widget, float)
  [custom parameters specific to the patch node]

Outputs:
  MODEL → KSampler.model
```

### 3. CLIPTextEncode (positive)

```
Inputs:
  text: "a highly detailed photograph of a mountain landscape"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → KSampler.positive
```

### 4. CLIPTextEncode (negative)

```
Inputs:
  text: "blurry, low quality, distorted"
  clip: ← CheckpointLoaderSimple.CLIP

Outputs:
  CONDITIONING → KSampler.negative
```

### 5. EmptyLatentImage

```
Inputs:
  width:      1024                                 (widget, int)
  height:     1024                                 (widget, int)
  batch_size: 1                                    (widget, int)

Outputs:
  LATENT → KSampler.latent_image
```

### 6. KSampler

```
Inputs:
  model:        ← ModelPatchNode.MODEL
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

### 7. VAEDecode

```
Inputs:
  samples: ← KSampler.LATENT
  vae:     ← CheckpointLoaderSimple.VAE

Outputs:
  IMAGE → SaveImage.images
```

### 8. SaveImage

```
Inputs:
  images: ← VAEDecode.IMAGE
  filename_prefix: "patched"
```

## Writing Custom Patch Nodes

### Core API Pattern

```python
class MyModelPatch:
    """Custom model patch node for ComfyUI."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch"
    CATEGORY = "model/patch"

    def patch(self, model, strength):
        # CRITICAL: clone the model to avoid modifying the original
        m = model.clone()

        # Access transformer options for hook registration
        # m.model_options["transformer_options"] is the dict for patches

        # Example: register a custom attention processor
        def custom_attn_fn(q, k, v, extra_options):
            # q, k, v are tensors: [batch, heads, seq_len, dim]
            # Modify attention here
            return k * strength, v * strength

        # Set transformer options
        m.model_options["transformer_options"]["my_custom_fn"] = custom_attn_fn

        return (m,)
```

### model.clone() Behavior

```python
m = model.clone()
```

- Creates a shallow copy of the model object
- `m.model_options` is deep-copied — safe to modify without affecting the original
- `m.model.model` (the actual neural network) is shared — weight modifications affect both
- Always clone before patching to prevent side effects

### model_options["transformer_options"]

This dict controls hooks into the model's attention and feed-forward layers:

```python
m.model_options["transformer_options"] = {
    # Pre-existing keys from other patches
    "patches": {...},
    "cond_or_uncond": [...],

    # Your custom keys
    "my_custom_fn": my_function,
    "my_attention_scale": 1.5,
}
```

Common transformer_options keys:

| Key | Type | Purpose |
|---|---|---|
| `patches` | dict | Registered patch functions by name |
| `cond_or_uncond` | list | Per-batch conditioning mode indicator |
| `attn_bias` | tensor | Attention bias added to attention scores |
| `positive` | tensor | Positive conditioning embeddings |
| `negative` | tensor | Negative conditioning embeddings |
| Custom keys | any | Your own data — accessed in patched functions |

### Monkey-Patching Forward Methods

Replace a layer's forward method to intercept computation:

```python
def patch(self, model, strength):
    m = model.clone()

    # Store original forward method
    original_forward = m.model.diffusion_model.middle_block.forward

    def patched_forward(x, context=None, **kwargs):
        # Pre-processing
        x = x * strength

        # Call original
        result = original_forward(x, context=context, **kwargs)

        # Post-processing
        return result * (1.0 / strength)

    # Replace forward method
    m.model.diffusion_model.middle_block.forward = patched_forward

    return (m,)
```

### Attention Hook Pattern

```python
def patch(self, model, scale):
    m = model.clone()

    def attn_hook(q, k, v, extra_options):
        """Called before attention computation.

        Args:
            q: Query tensor [batch*heads, seq_len, dim]
            k: Key tensor [batch*heads, seq_len, dim]
            v: Value tensor [batch*heads, seq_len, dim]
            extra_options: dict with 'block', 'block_index', etc.

        Returns:
            (modified_k, modified_v)
        """
        # Example: scale keys to control attention sharpness
        k = k * scale
        return k, v

    # Register the hook
    m.model_options["transformer_options"]["patches"]["attn"] = [attn_hook]

    return (m,)
```

### Sampling Hook Pattern

```python
def patch(self, model, step_offset):
    m = model.clone()

    def sample_hook(args):
        """Called at each sampling step.

        Args:
            args: dict with 'input', 'sigma', 'cond', 'uncond', etc.
        """
        # Modify the denoised prediction
        denoised = args["denoised"]
        # Apply custom logic
        return denoised

    m.model_options["transformer_options"]["patches"]["sample"] = [sample_hook]

    return (m,)
```

## Common Patch Patterns

### Attention Scaling

Control attention sharpness globally:

```python
def patch(self, model, scale):
    m = model.clone()
    m.model_options["transformer_options"]["attn_scale"] = scale
    return (m,)
```

### Cross-Attention Injection

Inject external features into cross-attention:

```python
def patch(self, model, features):
    m = model.clone()
    m.model_options["transformer_options"]["injection_features"] = features
    # Register a hook that concatenates features to k/v
    return (m,)
```

### Custom Sigma Schedule

Modify the noise schedule during sampling:

```python
def patch(self model, shift):
    m = model.clone()

    def sigma_hook(sigmas):
        # Shift the sigma schedule
        return sigmas * shift

    m.model_options["transformer_options"]["patches"]["sigmas"] = [sigma_hook]
    return (m,)
```

### Layer-Specific Modification

Patch only specific layers by checking `extra_options`:

```python
def attn_hook(q, k, v, extra_options):
    block = extra_options.get("block", None)
    if block == "middle":
        # Only modify middle block attention
        k = k * 2.0
    return k, v
```

## Key Considerations

- **Always clone**: `model.clone()` is mandatory before any modification. Modifying the original model affects all subsequent uses and can corrupt the workflow.
- **Patch ordering**: Multiple patches are applied in registration order. If two patches modify the same hook, the last one registered wins (or they compose, depending on hook type).
- **VRAM**: Cloning adds minimal overhead (shallow copy), but patches that store tensors or create new modules increase memory usage.
- **Compatibility**: Patches are model-architecture-specific. A patch designed for SDXL's attention structure won't work on SD1.5 or Flux.
- **Debugging**: Use `print()` inside patch functions to inspect tensor shapes and values. ComfyUI logs these to the console.
- **Reversibility**: Cloned models are independent. The original model is unchanged. Discard the cloned model by not connecting it.
- **transformer_options lifecycle**: Options are set once at clone time and accessed during every forward pass. They persist for the entire sampling process.
- **Custom node packs**: Many model patches are available in community node packs (e.g., ComfyUI-Advanced-ControlNet, ComfyUI-Inspire-Pack, ComfyUI-Impact-Pack). Check before writing from scratch.

## Advanced Patch Patterns

### Attention Optimization Chain

Chain multiple attention optimizations for maximum performance and quality:

```
CheckpointLoaderSimple
  └── MODEL → SageAttentionNode.model

SageAttentionNode
  └── MODEL → MemoryEfficientAttentionNode.model

MemoryEfficientAttentionNode
  └── MODEL → ChunkFeedForwardNode.model

ChunkFeedForwardNode
  └── MODEL → AttentionTunerNode.model

AttentionTunerNode
  └── MODEL → KSampler.model
```

#### SageAttention

Applies SageAttention — an optimized attention implementation that reduces memory usage and increases speed:

```
Inputs:
  model:  ← CheckpointLoaderSimple.MODEL
  attn_sage: true                                 (widget, bool)

Outputs:
  MODEL → MemoryEfficientAttentionNode.model
```

#### MemoryEfficientAttention

Enables memory-efficient attention computation (xformers or similar):

```
Inputs:
  model:  ← SageAttentionNode.MODEL

Outputs:
  MODEL → ChunkFeedForwardNode.model
```

#### ChunkFeedForward

Splits feed-forward computation into chunks to reduce peak VRAM:

```
Inputs:
  model:       ← MemoryEfficientAttentionNode.MODEL
  chunk_size:  1024                               (widget, int)

Outputs:
  MODEL → AttentionTunerNode.model
```

#### AttentionTuner

Fine-tunes attention parameters for quality/speed tradeoff:

```
Inputs:
  model:  ← ChunkFeedForwardNode.MODEL
  scale:  1.0                                     (widget, float)

Outputs:
  MODEL → KSampler.model
```

### NAG (Negative Guidance)

Enhanced negative prompting via the LTX2_NAG node — stronger negative guidance than standard CFG negative conditioning:

```
CheckpointLoaderSimple
  ├── MODEL → LTX2_NAG.model
  └── CLIP  → CLIPTextEncode.clip

CLIPTextEncode (positive)
  └── CONDITIONING → LTX2_NAG.positive

CLIPTextEncode (negative)
  └── CONDITIONING → LTX2_NAG.negative

LTX2_NAG
  └── MODEL → KSampler.model

KSampler
  cfg: 1.0  (NAG replaces CFG-based negative guidance)
```

#### LTX2_NAG Node

```
Inputs:
  model:      ← CheckpointLoaderSimple.MODEL
  positive:   ← CLIPTextEncode.positive
  negative:   ← CLIPTextEncode.negative
  nag_scale:  5.0                                 (widget, float)
  nag_tau:    5.0                                 (widget, float)

Outputs:
  MODEL → KSampler.model
```

**NAG parameters:**
- `nag_scale`: Strength of negative guidance (higher = stronger negative effect)
- `nag_tau`: Threshold for negative guidance activation

**When to use NAG:**
- Standard CFG negative prompting is insufficient
- You need stronger avoidance of specific concepts
- Using distilled models where CFG=1 is required (NAG provides the negative guidance that CFG would normally handle)

### ManualSigmas

Explicit sigma schedule strings for full control over the noise schedule:

```
ManualSigmasNode
  sigmas_string: "14.615, 10.0, 7.0, 5.0, 3.5, 2.5, 1.7, 1.2, 0.8, 0.5, 0.3, 0.1"
  └── SIGMAS → KSampler.sigmas
```

#### ManualSigmas Node

```
Inputs:
  sigmas_string: "14.615, 10.0, 7.0, 5.0, 3.5, 2.5, 1.7, 1.2, 0.8, 0.5, 0.3, 0.1"
                                     (widget, string — comma-separated float values)
  interpolate: true                  (widget, bool — linearly interpolate between values)

Outputs:
  SIGMAS → KSampler.sigmas
```

**When to use ManualSigmas:**
- Reproducing a specific noise schedule from a paper or recipe
- Fine-grained control over early/late denoising behavior
- Debugging sampler behavior at specific noise levels
- Matching schedules across different samplers

**Format:**
- Comma-separated float values
- Values must be in descending order (highest to lowest)
- First value = initial noise level (typically 14.615 for SDXL, varies by model)
- Last value should be near 0 (final clean state)
- Number of values determines effective step count

### CFG=1 for Distilled Models

Distilled models (e.g., LTXV distilled, Flux distilled) are trained to operate at CFG=1.0. Using higher CFG values produces over-saturated, artifact-heavy outputs:

```
KSampler
  cfg: 1.0    (MANDATORY for distilled models)
  steps: 8-12 (distilled models need fewer steps)
```

**Why CFG=1:**
- Distilled models incorporate classifier-free guidance internally during training
- External CFG multiplies the already-guided prediction, causing double-guidance
- CFG=1.0 means no external guidance modification — the model's prediction is used directly

**Compatible with NAG:**
When using a distilled model with NAG, set CFG=1.0 and let NAG handle negative guidance:

```
KSampler
  cfg: 1.0
LTX2_NAG
  nag_scale: 5.0
```

## Example Widget Values

### Simple Attention Scale

```
CheckpointLoaderSimple: ckpt_name = "sd_xl_base_1.0.safetensors"
ModelPatchNode: strength = 1.5
CLIPTextEncode: text = "a highly detailed portrait, sharp focus"
KSampler: seed=42, steps=30, cfg=7.0, sampler_name="dpmpp_2m", scheduler="karras"
```

### Custom Sampling Hook

```
CheckpointLoaderSimple: ckpt_name = "juggernautXL_v9.safetensors"
ModelPatchNode: step_offset=5, strength=0.8
CLIPTextEncode: text = "abstract art, dynamic composition"
KSampler: seed=123, steps=25, cfg=6.5
```

### Full Attention Optimization Chain

```
CheckpointLoaderSimple: ckpt_name = "sdxl_base_v1.0.safetensors"
SageAttentionNode: attn_sage=true
MemoryEfficientAttentionNode: (default settings)
ChunkFeedForwardNode: chunk_size=1024
AttentionTunerNode: scale=1.0
KSampler: seed=42, steps=30, cfg=7.0
```

### Distilled Model with NAG

```
CheckpointLoaderSimple: ckpt_name = "ltxv-distilled.safetensors"
LTX2_NAG: nag_scale=5.0, nag_tau=5.0
KSampler: seed=42, steps=8, cfg=1.0, sampler_name="euler", scheduler="normal"
```

### ManualSigmas Schedule

```
ManualSigmasNode: sigmas_string="14.615, 10.0, 7.0, 5.0, 3.5, 2.5, 1.7, 1.2, 0.8, 0.5, 0.3, 0.1"
KSampler: steps=12, cfg=7.0
```
