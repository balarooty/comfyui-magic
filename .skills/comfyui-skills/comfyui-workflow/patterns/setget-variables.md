# SetNode/GetNode Variable System

## When to Use

Eliminate wire spaghetti by creating named variables that any node can read. Use when your workflow has many nodes that need the same value (e.g., model, VAE, fps, frame count) and connecting them all with individual wires creates visual clutter. SetNode/GetNode replaces long-distance wires with a clean variable-based architecture.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `SetNode` | Stores a value under a unique name |
| `GetNode` | Retrieves a value by name from anywhere in the graph |

## Connection Order

### Basic Pattern

```
CheckpointLoaderSimple
  ├── MODEL → SetNode_MODEL.value
  ├── CLIP  → SetNode_CLIP.value
  └── VAE   → SetNode_VAE.value

SetNode_MODEL
  name: "MODEL_FULL"
  └── (stored as variable "MODEL_FULL")

SetNode_CLIP
  name: "CLIP_ENCODER"
  └── (stored as variable "CLIP_ENCODER")

SetNode_VAE
  name: "VAE_VIDEO"
  └── (stored as variable "VAE_VIDEO")

# Anywhere in the graph:
GetNode_MODEL
  name: "MODEL_FULL"
  └── MODEL → KSampler.model

GetNode_VAE
  name: "VAE_VIDEO"
  └── VAE → VAEDecode.vae

GetNode_CLIP
  name: "CLIP_ENCODER"
  └── CLIP → CLIPTextEncode.clip
```

### Multi-Consumer Pattern

One SetNode feeds multiple GetNodes:

```
SetNode_FPS
  name: "FPS_FLOAT"
  value: 24.0
  └── (stored as variable "FPS_FLOAT")

GetNode_FPS_1  (in video output section)
  name: "FPS_FLOAT"
  └── FLOAT → VideoCombine.fps

GetNode_FPS_2  (in audio section)
  name: "FPS_FLOAT"
  └── FLOAT → AudioSync.target_fps

GetNode_FPS_3  (in preview section)
  name: "FPS_FLOAT"
  └── FLOAT → PreviewWidget.display_fps
```

## Variable Naming Conventions

### Recommended Naming Pattern

```
TYPE_CONTEXT

Examples:
  MODEL_FULL          — Full precision model
  MODEL_PRUNED        — Pruned model
  MODEL_LORA_1        — Model after first LoRA
  CLIP_ENCODER        — CLIP model for encoding
  CLIP_NEGATIVE       — CLIP for negative prompts
  VAE_VIDEO           — Video VAE
  VAE_IMAGE           — Image VAE
  FPS_FLOAT           — Frame rate as float
  FRAME_COUNT_INT     — Number of frames
  WIDTH_INT           — Image/video width
  HEIGHT_INT          — Image/video height
  SEED_INT            — Random seed
  PROMPT_POSITIVE     — Positive conditioning
  PROMPT_NEGATIVE     — Negative conditioning
  LATENT_INPUT        — Input latent
  LATENT_OUTPUT       — Output latent
```

### Naming Rules

- Names are case-sensitive
- Must be unique within a workflow
- No spaces (use underscores)
- Include type suffix for clarity (`_INT`, `_FLOAT`, `_MODEL`, `_VAE`)
- Include context to disambiguate (`_VIDEO`, `_IMAGE`, `_FULL`)

## Wiring Patterns

### Centralized Model Distribution

```
# SINGLE SOURCE
CheckpointLoaderSimple
  MODEL → SetNode_MODEL.value
  CLIP  → SetNode_CLIP.value
  VAE   → SetNode_VAE.value

# MULTIPLE CONSUMERS
GetNode_MODEL → KSampler_1.model
GetNode_MODEL → KSampler_2.model
GetNode_MODEL → ModelPatchNode.model
GetNode_MODEL → LoRALoader.model

GetNode_VAE → VAEDecode_1.vae
GetNode_VAE → VAEDecode_2.vae
GetNode_VAE → VAEEncode.vae
```

### Configuration Hub

```
# DEFINE ALL CONFIG IN ONE PLACE
SetNode_WIDTH
  name: "WIDTH_INT"
  value: 1024

SetNode_HEIGHT
  name: "HEIGHT_INT"
  value: 1024

SetNode_FPS
  name: "FPS_FLOAT"
  value: 24.0

SetNode_FRAMES
  name: "FRAME_COUNT_INT"
  value: 97

SetNode_SEED
  name: "SEED_INT"
  value: 42

# CONSUME ANYWHERE
GetNode_WIDTH  → EmptyLatentImage.width
GetNode_HEIGHT → EmptyLatentImage.height
GetNode_FPS    → VideoCombine.fps
GetNode_FRAMES → EmptyLTXVLatentVideo.frame_count
GetNode_SEED   → KSampler.seed
```

### Pipeline Stage Isolation

```
# STAGE 1: ENCODING
SetNode_PROMPT_POS
  name: "CONDITIONING_POSITIVE"
  value: ← CLIPTextEncode (positive).CONDITIONING

SetNode_PROMPT_NEG
  name: "CONDITIONING_NEGATIVE"
  value: ← CLIPTextEncode (negative).CONDITIONING

# STAGE 2: SAMPLING (reads from Stage 1)
GetNode_PROMPT_POS → KSampler.positive
GetNode_PROMPT_NEG → KSampler.negative

# STAGE 3: DECODING (reads from Stage 2)
SetNode_LATENT
  name: "LATENT_SAMPLED"
  value: ← KSampler.LATENT

GetNode_LATENT → VAEDecode.samples
```

## Key Considerations

- **Uniqueness**: Each SetNode name must be unique. Duplicate names cause undefined behavior — the last SetNode registered wins, but ordering is not guaranteed.
- **Type safety**: GetNode infers type from the connected SetNode. Connecting a MODEL GetNode to a VAE input causes a type error.
- **Direction**: SetNode is write-only (input side). GetNode is read-only (output side). You cannot read from a SetNode or write to a GetNode.
- **Scope**: Variables are workflow-global. There is no local scoping. A SetNode in one part of the graph is accessible everywhere.
- **No cycles**: You cannot have SetNode A reference GetNode B which references SetNode A. This creates a circular dependency.
- **Performance**: Zero overhead at runtime. SetNode/GetNode are resolved during graph compilation, not during execution.
- **Debugging**: When a GetNode produces unexpected output, find its SetNode by name. The SetNode's input wire shows the source.
- **Refactoring**: To change a value source, only modify the SetNode's input. All GetNodes automatically receive the new value.
- **Wire reduction**: A workflow with 20 nodes sharing a model can use 1 SetNode + 19 GetNodes instead of 19 separate wires from the loader.

## Example Widget Values

### Configuration Hub

```
SetNode_MODEL:  name="MODEL_FULL"
SetNode_CLIP:   name="CLIP_ENCODER"
SetNode_VAE:    name="VAE_VIDEO"
SetNode_WIDTH:  name="WIDTH_INT",    value=1024
SetNode_HEIGHT: name="HEIGHT_INT",   value=1024
SetNode_FPS:    name="FPS_FLOAT",    value=24.0
SetNode_FRAMES: name="FRAME_COUNT_INT", value=97
SetNode_SEED:   name="SEED_INT",     value=42
```

### Multi-Model Workflow

```
SetNode_BASE:    name="MODEL_BASE"     ← CheckpointLoader (base)
SetNode_REFINER: name="MODEL_REFINER"  ← CheckpointLoader (refiner)
SetNode_UPSCALE: name="MODEL_UPSCALE"  ← UpscaleModelLoader

GetNode_BASE    → KSampler_base.model
GetNode_REFINER → KSampler_refiner.model
GetNode_UPSCALE → ImageUpscale.model
```
