# controlnet-stack

Multi-ControlNet stacking pipeline for precise spatial control.

## When to Use

- Combining multiple spatial controls (pose + depth + canny)
- When a single ControlNet isn't sufficient for the desired output
- Fine-grained control over composition, structure, and style

## Required Nodes

| Node Type | Quantity | Purpose |
|---|---|---|
| `CheckpointLoaderSimple` | 1 | Loads model, CLIP, and VAE |
| `CLIPTextEncode` (positive) | 1 | Encodes positive prompt |
| `CLIPTextEncode` (negative) | 1 | Encodes negative prompt |
| `EmptyLatentImage` | 1 | Creates blank latent |
| `ControlNetLoader` | 2+ | Loads each ControlNet model |
| `ControlNetApplyAdvanced` | 2+ | Applies each ControlNet to conditioning |
| `LoadImage` | 2+ | Loads control images (pose, depth, canny, etc.) |
| `KSampler` | 1 | Runs diffusion sampling |
| `VAEDecode` | 1 | Decodes latent to image |
| `SaveImage` | 1 | Saves output |

## Node-by-Node Wiring Guide

### 1. CheckpointLoaderSimple

- **Outputs:** `MODEL`, `CLIP`, `VAE`
- **Widget:** `ckpt_name` — e.g. `"v1-5-pruned-emaonly.safetensors"`

### 2. CLIPTextEncode (positive)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — e.g. `"a woman standing in a garden, detailed, high quality"`
- **Output:** `CONDITIONING`

### 3. CLIPTextEncode (negative)

- **Input:** `CLIP` ← from CheckpointLoaderSimple
- **Widget:** `text` — e.g. `"blurry, deformed, low quality"`
- **Output:** `CONDITIONING`

### 4. EmptyLatentImage

- **Widgets:** `width`=512, `height`=512, `batch_size`=1
- **Output:** `LATENT`

### 5. ControlNetLoader (ControlNet A)

- **Widget:** `control_net_name` — e.g. `"control_v11p_sd15_openpose.pth"`
- **Output:** `CONTROL_NET`

### 6. ControlNetLoader (ControlNet B)

- **Widget:** `control_net_name` — e.g. `"control_v11f1p_sd15_depth.pth"`
- **Output:** `CONTROL_NET`

### 7. LoadImage (Control Image A — e.g. pose)

- **Widget:** `image` — e.g. `"pose.png"`
- **Output:** `IMAGE`, `MASK`

### 8. LoadImage (Control Image B — e.g. depth)

- **Widget:** `image` — e.g. `"depth.png"`
- **Output:** `IMAGE`, `MASK`

### 9. ControlNetApplyAdvanced (first — e.g. OpenPose)

- **Inputs:**
  - `positive` ← from CLIPTextEncode (positive)
  - `negative` ← from CLIPTextEncode (negative)
  - `control_net` ← from ControlNetLoader (A)
  - `image` ← from LoadImage (A)
- **Widgets:**
  - `strength` — e.g. `0.8` (how strongly this control influences output)
  - `start_percent` — e.g. `0.0`
  - `end_percent` — e.g. `1.0`
- **Outputs:** `positive`, `negative` (modified conditioning)

### 10. ControlNetApplyAdvanced (second — e.g. Depth)

- **Inputs:**
  - `positive` ← from ControlNetApplyAdvanced (first) [positive output]
  - `negative` ← from ControlNetApplyAdvanced (first) [negative output]
  - `control_net` ← from ControlNetLoader (B)
  - `image` ← from LoadImage (B)
- **Widgets:**
  - `strength` — e.g. `0.6`
  - `start_percent` — e.g. `0.0`
  - `end_percent` — e.g. `1.0`
- **Outputs:** `positive`, `negative` (further modified conditioning)

### 11. KSampler

- **Inputs:**
  - `model` ← from CheckpointLoaderSimple
  - `positive` ← from ControlNetApplyAdvanced (second) [positive]
  - `negative` ← from ControlNetApplyAdvanced (second) [negative]
  - `latent_image` ← from EmptyLatentImage
- **Widgets:** `seed`=42, `steps`=20, `cfg`=7.0, `sampler_name`="euler", `scheduler`="normal", `denoise`=1.0
- **Output:** `LATENT`

### 12. VAEDecode → SaveImage

- Standard decode and save chain

## Connection Order

```
CheckpointLoaderSimple ─┬─ MODEL ──────────────────────────────────────► KSampler
                        ├─ CLIP ──┬────────────────────────────────────► CLIPTextEncode (pos/neg)
                        └─ VAE ────────────────────────────────────────► VAEDecode

ControlNetLoader (A) ──── CONTROL_NET ──────────────► ControlNetApply (A)
LoadImage (A) ─────────── IMAGE ────────────────────► ControlNetApply (A)

ControlNetLoader (B) ──── CONTROL_NET ──────────────► ControlNetApply (B)
LoadImage (B) ─────────── IMAGE ────────────────────► ControlNetApply (B)

CLIPTextEncode (pos) ──── CONDITIONING [positive] ──► ControlNetApply (A) [positive]
CLIPTextEncode (neg) ──── CONDITIONING [negative] ──► ControlNetApply (A) [negative]

ControlNetApply (A) pos ─► ControlNetApply (B) [positive]
ControlNetApply (A) neg ─► ControlNetApply (B) [negative]

ControlNetApply (B) pos ─► KSampler [positive]
ControlNetApply (B) neg ─► KSampler [negative]

EmptyLatentImage ────────► KSampler [latent_image]
KSampler ────────────────► VAEDecode ───────────────► SaveImage
```

## Key Considerations

- **Order matters:** Apply ControlNets in priority order. The first ControlNet applied has the strongest structural influence because later ones modify already-modified conditioning.
- **Strength balancing:** When stacking, reduce individual strengths (e.g. 0.6-0.8 each) to avoid over-constraining. Combined strengths near 1.0+ per control can cause artifacts.
- **start_percent / end_percent:** Control when each ControlNet is active during sampling. For example, `start_percent=0.0, end_percent=0.8` means the control releases before the final steps, allowing fine details to be unconstrained.
- **Control image preprocessing:** Control images must match the expected format (OpenPose skeletons, depth maps, canny edges). Use dedicated preprocessors if needed.
- **Compatibility:** All ControlNets must be for the same base model (SD 1.5 ControlNets with SD 1.5 checkpoints, etc.).
