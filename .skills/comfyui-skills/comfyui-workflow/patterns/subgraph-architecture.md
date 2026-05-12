# Subgraph Architecture Pattern

## When to Use

Encapsulate reusable pipeline components into self-contained modules. Use when you have a multi-node sequence that repeats across workflows (e.g., a standard encoding pipeline, a post-processing chain, or a video output setup). Subgraphs reduce visual complexity, enable parameterized reuse, and enforce consistent configurations across projects.

## Required Nodes

| Node Type | Purpose |
|---|---|
| `Subgraph` | Container node that wraps an internal workflow |
| `SubgraphInput` (internal) | Exposes values from outside the subgraph |
| `SubgraphOutput` (internal) | Sends values back outside the subgraph |
| `ProxyWidget` (internal) | Maps external widget values to internal nodes |

## Connection Order

### External View

```
SubgraphNode (visible in parent workflow)
  ├── INPUT_1: width    ← upstream node or widget
  ├── INPUT_2: height   ← upstream node or widget
  ├── INPUT_3: model    ← CheckpointLoaderSimple.MODEL
  └── OUTPUT_1: latent  → downstream node
```

### Internal View (inside subgraph editor)

```
SubgraphInput
  ├── width  → ProxyWidget_width → EmptyLatentImage.width
  ├── height → ProxyWidget_height → EmptyLatentImage.height
  └── model  → KSampler.model

EmptyLatentImage
  └── LATENT → KSampler.latent_image

KSampler
  └── LATENT → SubgraphOutput.input
```

## Subgraph Creation Workflow

### Step 1: Build the Internal Pipeline

Create the nodes you want to encapsulate:

```
EmptyLatentImage → KSampler → VAEDecode
```

### Step 2: Add SubgraphInput/Output Nodes

```
SubgraphInput
  ├── width  → EmptyLatentImage.width
  ├── height → EmptyLatentImage.height
  ├── model  → KSampler.model
  └── seed   → KSampler.seed

KSampler
  └── LATENT → VAEDecode.samples

VAEDecode
  └── IMAGE → SubgraphOutput.images
```

### Step 3: Expose Configurable Inputs

Each `SubgraphInput` output becomes an input slot on the subgraph node:

```
SubgraphInput outputs:
  [0] width   → maps to EmptyLatentImage.width
  [1] height  → maps to EmptyLatentImage.height
  [2] model   → maps to KSampler.model
  [3] seed    → maps to KSampler.seed
```

### Step 4: Add Proxy Widgets for Defaults

```
ProxyWidget (width)
  target: EmptyLatentImage.width
  default: 1024
  min: 64
  max: 4096
  step: 64

ProxyWidget (height)
  target: EmptyLatentImage.height
  default: 1024
  min: 64
  max: 4096
  step: 64
```

## Proxy Widget Mapping

Proxy widgets bridge external values to internal node widgets:

```
External Input → ProxyWidget → Internal Node Widget

width (int)    → ProxyWidget → EmptyLatentImage.width
height (int)   → ProxyWidget → EmptyLatentImage.height
fps (float)    → ProxyWidget → VideoCombine.fps
cfg (float)    → ProxyWidget → KSampler.cfg
steps (int)    → ProxyWidget → KSampler.steps
sampler (enum) → ProxyWidget → KSampler.sampler_name
```

### ProxyWidget Configuration

```python
# Internal to ComfyUI — configured via the subgraph editor
{
    "target_node_id": 5,           # Node ID within subgraph
    "target_widget_name": "width", # Widget name on target node
    "default_value": 1024,
    "min": 64,
    "max": 4096,
    "step": 64,
    "display_name": "Width"        # Label shown on subgraph node
}
```

## Subgraph Reuse Patterns

### Pattern 1: Standard Encode Pipeline

```
Subgraph: "EncodePipeline"
  Inputs:  model, clip, positive_text, negative_text
  Outputs: positive_conditioning, negative_conditioning

Internal:
  CLIPTextEncode (positive) ← clip + positive_text
  CLIPTextEncode (negative) ← clip + negative_text
```

### Pattern 2: Video Output Pipeline

```
Subgraph: "VideoOutput"
  Inputs:  images, fps, filename_prefix
  Outputs: video_path

Internal:
  VideoCombine ← images + fps
  SaveVideo ← filename_prefix
```

### Pattern 3: Post-Processing Chain

```
Subgraph: "PostProcess"
  Inputs:  image, sharpen_amount, denoise_amount
  Outputs: processed_image

Internal:
  ImageSharpen ← sharpen_amount
  ImageDenoise ← denoise_amount
```

### Pattern 4: Parameterized Sampler

```
Subgraph: "SmartSampler"
  Inputs:  model, positive, negative, latent, seed, quality_preset
  Outputs: latent

Internal:
  # quality_preset maps to steps/cfg via logic
  KSampler ← all inputs
```

## Key Considerations

- **Scope isolation**: Nodes inside a subgraph cannot directly connect to nodes outside it. All data must flow through SubgraphInput/SubgraphOutput.
- **Widget override**: Proxy widgets with defaults can be overridden by connecting an input wire. If no wire is connected, the default value is used.
- **Nesting**: Subgraphs can contain other subgraphs. Deep nesting (>3 levels) makes debugging difficult.
- **Performance**: Subgraphs have zero runtime overhead. They are purely a visual/organizational construct — ComfyUI flattens them during execution.
- **Serialization**: Subgraphs are stored as nested workflow JSON. The parent workflow contains a reference to the subgraph's internal node graph.
- **Version control**: When sharing workflows, subgraph definitions are embedded in the workflow file. No external dependencies.
- **Debugging**: Use the subgraph editor to inspect internal node states. Some hosts support breakpoint-style debugging inside subgraphs.
- **Input validation**: Proxy widgets enforce min/max constraints. Invalid external values are clamped before reaching internal nodes.
- **Naming**: Give subgraphs descriptive names (e.g., "LTXV Encode Pipeline" not "Subgraph1"). Names appear in the workflow editor and affect readability.

## Example Widget Values

### Standard Encode Pipeline Subgraph

```
Subgraph: "EncodePipeline"
  Inputs:
    model: ← CheckpointLoaderSimple.MODEL
    clip:  ← CheckpointLoaderSimple.CLIP
    positive_text: "a beautiful sunset over the ocean"
    negative_text: "blurry, low quality"

  Internal ProxyWidgets:
    positive_text.default: ""
    negative_text.default: ""

  Outputs:
    positive: → KSampler.positive
    negative: → KSampler.negative
```

### Parameterized Sampler Subgraph

```
Subgraph: "SmartSampler"
  Inputs:
    model:        ← upstream model
    positive:     ← upstream conditioning
    negative:     ← upstream conditioning
    latent:       ← upstream latent
    seed:         42
    quality:      "balanced"  (enum: "fast", "balanced", "quality")

  Internal ProxyWidgets:
    seed.default: 42
    quality.default: "balanced"
    quality.values: ["fast", "balanced", "quality"]

  Internal Logic:
    fast:     steps=15, cfg=7.0
    balanced: steps=25, cfg=7.0
    quality:  steps=40, cfg=8.0

  Outputs:
    latent: → VAEDecode.samples
```
