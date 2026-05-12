# ComfyUI Design Patterns

Pipeline architecture patterns for building ComfyUI workflows.

---

## 1. Linear Pipeline

The most common and straightforward pattern. Data flows in a single path from input to output.

### When to Use

- Simple text-to-image generation
- Basic image processing
- Learning and prototyping
- When you need a single, predictable output

### Required Nodes

```
CheckpointLoaderSimple → CLIPTextEncode (positive)
                      → CLIPTextEncode (negative)
                      → EmptyLatentImage
                      → KSampler
                      → VAEDecode
                      → SaveImage
```

### Connection Order

```
1. CheckpointLoaderSimple
   ├── MODEL → KSampler.model
   ├── CLIP  → CLIPTextEncode.positive.clip
   └── CLIP  → CLIPTextEncode.negative.clip

2. CLIPTextEncode (positive)
   └── CONDITIONING → KSampler.positive

3. CLIPTextEncode (negative)
   └── CONDITIONING → KSampler.negative

4. EmptyLatentImage
   └── LATENT → KSampler.latent_image

5. KSampler
   └── LATENT → VAEDecode.samples

6. VAEDecode (VAE from CheckpointLoaderSimple)
   └── IMAGE → SaveImage
```

### Key Considerations

- The VAE output from CheckpointLoaderSimple connects to VAEDecode
- Both CLIPTextEncode nodes share the same CLIP source
- EmptyLatentImage determines output resolution
- KSampler denoise=1.0 for txt2img, <1.0 for img2img

---

## 2. Branching Pipeline

A single source feeds multiple independent paths that may converge at the end.

### When to Use

- Generating multiple variations from the same model
- Comparing different prompts with the same settings
- Processing the same latent with different decoders
- A/B testing configurations

### Required Nodes

```
CheckpointLoaderSimple → CLIPTextEncode (prompt A) → KSampler A → VAEDecode A → SaveImage A
                      → CLIPTextEncode (prompt B) → KSampler B → VAEDecode B → SaveImage B
                      → EmptyLatentImage (shared)
```

### Connection Order

```
1. CheckpointLoaderSimple (single source)
   ├── MODEL  → KSampler A.model, KSampler B.model
   ├── CLIP   → CLIPTextEncode A.clip, CLIPTextEncode B.clip
   └── VAE    → VAEDecode A.vae, VAEDecode B.vae

2. EmptyLatentImage (shared)
   └── LATENT → KSampler A.latent_image, KSampler B.latent_image

3. Each branch operates independently:
   CLIPTextEncode A → KSampler A → VAEDecode A → SaveImage A
   CLIPTextEncode B → KSampler B → VAEDecode B → SaveImage B
```

### Key Considerations

- Branches can have different seeds for variation
- Use different file prefixes to distinguish outputs
- Branches execute in parallel when possible
- Consider using groups to visually separate branches

---

## 3. Multi-Pass Pipeline

Generate a base image, then refine it through multiple passes.

### When to Use

- High-quality image generation with refinement
- Inpainting workflows (generate → mask → regenerate)
- Detail enhancement passes
- Super-resolution pipelines

### Required Nodes

```
CheckpointLoaderSimple → KSampler (pass 1) → VAEDecode → ImageScale → VAEEncode → KSampler (pass 2) → VAEDecode → SaveImage
```

### Connection Order

```
Pass 1: Generate base
1. CheckpointLoaderSimple → KSampler (steps=20, denoise=1.0) → LATENT

Pass 2: Refine
2. LATENT → VAEDecode → IMAGE
3. IMAGE → ImageScale (upscale)
4. ImageScale → VAEEncode → LATENT (upscaled)
5. LATENT (upscaled) → KSampler (steps=10, denoise=0.5) → LATENT (refined)
6. LATENT (refined) → VAEDecode → IMAGE (final)
7. IMAGE → SaveImage
```

### Key Considerations

- Pass 1 uses high denoise (1.0) for generation
- Pass 2 uses lower denoise (0.3-0.6) for refinement
- Steps can be reduced in refinement passes
- Consider using a different sampler for refinement (e.g., dpmpp_2m for refinement)
- Use KSamplerAdvanced for precise step control in multi-pass

---

## 4. Model Patching Chain

Apply model modifications (LoRA, IP-Adapter, etc.) before sampling.

### When to Use

- Using LoRA for style/character consistency
- Applying IP-Adapter for image-guided generation
- Combining multiple model modifications
- Custom model conditioning

### Required Nodes

```
CheckpointLoaderSimple → LoraLoader → IPAdapterApply → KSampler
CLIPVisionLoader → IPAdapterModelLoader → IPAdapterApply
```

### Connection Order

```
1. CheckpointLoaderSimple
   ├── MODEL  → LoraLoader.model
   └── CLIP   → LoraLoader.clip

2. LoraLoader
   ├── MODEL  → IPAdapterApply.model
   └── CLIP   → CLIPTextEncode.clip

3. CLIPVisionLoader
   └── CLIP_VISION → IPAdapterApply.clip_vision

4. IPAdapterModelLoader
   └── IPADAPTER → IPAdapterApply.ipadapter

5. LoadImage (reference image)
   └── IMAGE → IPAdapterApply.image

6. IPAdapterApply
   └── MODEL → KSampler.model

7. CLIPTextEncode → KSampler.positive
8. EmptyLatentImage → KSampler.latent_image
9. KSampler → VAEDecode → SaveImage
```

### Key Considerations

- LoRA strength affects style intensity (0.5-1.0 typical)
- IP-Adapter weight controls reference image influence
- Multiple LoRAs can be chained: LoRA1 → LoRA2 → KSampler
- Order of patches matters: different order = different results
- Some patches modify CLIP, some modify MODEL, some modify both

---

## 5. Video Pipeline

Generate or process video with temporal consistency.

### When to Use

- Text-to-video generation
- Image animation
- Video style transfer
- Frame interpolation

### Required Nodes

```
CheckpointLoaderSimple → CLIPTextEncode → EmptyLatentImage → KSampler → VAEDecode → VHS_VideoCombine
AnimateDiffLoader → KSampler
```

### Connection Order

```
1. CheckpointLoaderSimple
   ├── MODEL → AnimateDiffLoader.model
   └── CLIP  → CLIPTextEncode.clip

2. AnimateDiffLoader
   └── MODEL → KSampler.model

3. CLIPTextEncode → KSampler.positive

4. EmptyLatentImage (batch_size=16 for 16 frames)
   └── LATENT → KSampler.latent_image

5. KSampler
   └── LATENT → VAEDecode.samples

6. VAEDecode
   └── IMAGE → VHS_VideoCombine.images

7. VHS_VideoCombine
   → Configure: frame_rate=8, format="image/gif"
```

### Key Considerations

- Batch size in EmptyLatentImage = number of frames
- AnimateDiff provides temporal consistency
- Frame rate affects playback speed (8-12 fps typical)
- Use consistent seeds across frames for coherence
- Consider frame interpolation for smoother output
- Video formats: GIF, WebP, MP4, WebM

---

## 6. ControlNet Stacking

Apply multiple ControlNet models sequentially for precise spatial control.

### When to Use

- Complex pose + depth + edge control
- Architectural visualization with multiple constraints
- Character consistency with pose + face control
- Fine-grained spatial composition

### Required Nodes

```
ControlNetLoader (depth) → ControlNetApplyAdvanced
ControlNetLoader (pose) → ControlNetApplyAdvanced
ControlNetLoader (canny) → ControlNetApplyAdvanced
```

### Connection Order

```
1. ControlNetLoader (depth)
   └── CONTROL_NET → ControlNetApplyAdvanced.control_net (first)

2. ControlNetLoader (pose)
   └── CONTROL_NET → ControlNetApplyAdvanced.control_net (second)

3. ControlNetLoader (canny)
   └── CONTROL_NET → ControlNetApplyAdvanced.control_net (third)

4. First ControlNetApplyAdvanced:
   ├── positive (from CLIPTextEncode) → output positive
   └── negative (from CLIPTextEncode) → output negative

5. Second ControlNetApplyAdvanced:
   ├── positive (from first) → output positive
   └── negative (from first) → output negative

6. Third ControlNetApplyAdvanced:
   ├── positive → KSampler.positive
   └── negative → KSampler.negative

7. Each ControlNetApplyAdvanced needs:
   ├── image (from LoadImage or preprocessors)
   ├── strength (0.0-1.0)
   ├── start_percent (0.0)
   └── end_percent (1.0)
```

### Key Considerations

- ControlNets are applied in sequence (chained)
- Each ControlNet can have independent strength
- Use start/end percentages to control when each ControlNet is active
- Lower strength values (0.3-0.7) prevent over-constraining
- Different preprocessors may be needed for different ControlNets

---

## 7. Prompt Scheduling

Switch prompts at different stages of sampling for temporal variation.

### When to Use

- Changing style mid-generation
- Transitioning between subjects
- Creating composite styles
- Time-based animation effects

### Required Nodes

```
CLIPTextEncode (prompt A) → ConditioningSetTimestepRange → ConditioningCombine
CLIPTextEncode (prompt B) → ConditioningSetTimestepRange → ConditioningCombine
```

### Connection Order

```
1. CLIPTextEncode (prompt A)
   └── CONDITIONING → ConditioningSetTimestepRange.conditioning
      (start_percent=0.0, end_percent=0.5)

2. CLIPTextEncode (prompt B)
   └── CONDITIONING → ConditioningSetTimestepRange.conditioning
      (start_percent=0.5, end_percent=1.0)

3. Both ConditioningSetTimestepRange outputs
   └── CONDITIONING → ConditioningCombine (or ConditioningConcat)

4. ConditioningCombine
   └── CONDITIONING → KSampler.positive

5. Rest of pipeline: KSampler → VAEDecode → SaveImage
```

### Key Considerations

- Prompt A applies from step 0% to 50%
- Prompt B applies from step 50% to 100%
- Smooth transitions use overlapping ranges
- Use ConditioningCombine for merging, ConditioningConcat for appending
- Advanced scheduling can use multiple ranges with different strengths

---

## 8. Audio-Reactive Pipeline

Use audio analysis to drive visual generation parameters.

### When to Use

- Music visualization
- Audio-driven animation
- Beat-synchronized effects
- Rhythmic pattern generation

### Required Nodes

```
Audio Analysis Node → Scheduler → ConditioningModifier → KSampler
```

### Connection Order

```
1. Load Audio
   └── AUDIO → AudioAnalyzer.input

2. AudioAnalyzer
   ├── BEAT → BeatScheduler.beats
   └── ENERGY → FloatToStrength.energy

3. BeatScheduler
   └── SIGMAS → SamplerCustom.sigmas

4. FloatToStrength
   └── FLOAT → ConditioningSetStrength.strength

5. ConditioningSetStrength
   └── CONDITIONING → KSampler.positive

6. KSampler → VAEDecode → VHS_VideoCombine
```

### Key Considerations

- Audio analysis extracts beats, energy, frequency bands
- Beat synchronization requires accurate BPM detection
- Strength modulation creates pulsing effects
- Consider smoothing for less jarring transitions
- Frame rate should match or be a multiple of audio sample rate

---

## 9. Dynamic Branching

Conditionally execute different paths based on runtime values.

### When to Use

- Conditional processing based on image properties
- Different pipelines for different input types
- Error handling with fallback paths
- A/B testing with random selection

### Required Nodes

```
ImageAnalyzer → ConditionRouter → Pipeline A or Pipeline B
```

### Connection Order

```
1. LoadImage
   ├── IMAGE → ImageAnalyzer.image
   └── IMAGE → Pipeline A.image, Pipeline B.image

2. ImageAnalyzer
   └── BOOLEAN → ConditionRouter.condition

3. ConditionRouter
   ├── true_path → Pipeline A (triggered when true)
   └── false_path → Pipeline B (triggered when false)

4. Pipeline A
   └── IMAGE → SaveImage (filename_prefix="A")

5. Pipeline B
   └── IMAGE → SaveImage (filename_prefix="B")
```

### Key Considerations

- ComfyUI evaluates all nodes by default; use lazy inputs for true conditional execution
- Both branches may be evaluated even if only one output is used
- Consider using Switch node for cleaner branching
- Seed management across branches for consistency

---

## 10. Batch Processing

Process multiple items in a loop or batch configuration.

### When to Use

- Processing multiple images with same settings
- Generating variations of a prompt
- Creating image grids
- Bulk operations on datasets

### Required Nodes

```
LoadImageBatch → KSampler (loop) → SaveImageBatch
```

### Connection Order

```
1. LoadImage (or LoadImageBatch)
   └── IMAGE → BatchProcess.input

2. CheckpointLoaderSimple
   ├── MODEL → KSampler.model
   └── CLIP  → CLIPTextEncode.clip

3. CLIPTextEncode → KSampler.positive

4. KSampler
   └── LATENT → VAEDecode.samples

5. VAEDecode
   └── IMAGE → SaveImage
```

### Key Considerations

- Use batch_size in EmptyLatentImage for parallel generation
- Each image in batch gets same seed (use seed+batch_index for variation)
- Batch processing increases VRAM usage proportionally
- Consider processing in smaller batches for memory efficiency
- Use different filename_prefix for each batch item

---

## 11. Audio-Video Fusion

Combine video and audio latents for unified sampling, then separate after generation.

### When to Use
- LTX Video with audio generation
- Music-synchronized video
- Audio-driven video effects

### Required Nodes
```
LTXVAudioVAELoader → LTXVEmptyLatentAudio → LTXVConcatAVLatent → SamplerCustomAdvanced → LTXVSeparateAVLatent → LTXVAudioVAEDecode → VHS_VideoCombine
```

### Connection Order
```
1. LTXVAudioVAELoader → VAE (audio)
2. LTXVEmptyLatentAudio (frame_count, frame_rate) → LATENT (audio)
3. EmptyLTXVLatentVideo (width, height, frame_count) → LATENT (video)
4. LTXVConcatAVLatent(video_latent, audio_latent) → LATENT (combined)
5. SamplerCustomAdvanced(noise, guider, sampler, sigmas, combined_latent) → LATENT (sampled)
6. LTXVSeparateAVLatent(sampled, frame_count) → video_latent, audio_latent
7. LTXVAudioVAEDecode(audio_latent, audio_vae, frame_rate) → AUDIO
8. LTXVSpatioTemporalTiledVAEDecode(video_latent, video_vae) → IMAGE
9. VHS_VideoCombine(images, audio, frame_rate)
```

### Key Considerations
- Frame rate must be consistent between video and audio latents
- Audio VAE and video VAE are separate models
- ConcatAVLatent merges before sampling for coherent generation
- SeparateAVLatent splits after sampling for independent decoding

---

## 12. Latent Upsampling

Generate at low resolution, then upscale in latent space for higher quality.

### When to Use
- High-resolution video generation
- Memory-efficient large image generation
- Progressive quality improvement

### Required Nodes
```
EmptyLTXVLatentVideo (low res) → SamplerCustomAdvanced → LTXVLatentUpsampler → SamplerCustomAdvanced (refinement) → VAEDecode
```

### Connection Order
```
1. EmptyLTXVLatentVideo (480×256, 97 frames) → LATENT (base)
2. SamplerCustomAdvanced (base) → LATENT (sampled low-res)
3. LatentUpscaleModelLoader (spatial-upscaler) → UPSCALE_MODEL
4. LTXVLatentUpsampler(model, sampled, upscale_model) → LATENT (upsampled)
5. SamplerCustomAdvanced (refinement, low denoise) → LATENT (refined)
6. VAEDecode (refined) → IMAGE
```

### Key Considerations
- Base generation at low res uses less VRAM
- Upscaler model is separate from the diffusion model
- Refinement pass uses low denoise (0.1-0.3)
- Two different sigmas: one for base, one for refinement

---

## 13. Two-Pass Sampling

Coarse pass for structure, fine pass for detail.

### When to Use
- High-quality video generation
- Distilled model refinement
- Detail enhancement

### Required Nodes
```
SamplerCustomAdvanced (pass 1: distilled) → LoraLoaderModelOnly (detailer) → SamplerCustomAdvanced (pass 2: refinement)
```

### Connection Order
```
1. Model + DistilledLoRA (strength=0.6) → Guider → SamplerCustomAdvanced (pass 1, sigmas="0.85,0.725,0.422,0.0")
2. Pass 1 output → LoraLoaderModelOnly (detailer, strength=1.0)
3. Detailer model → Guider → SamplerCustomAdvanced (pass 2, different sigmas)
4. Pass 2 output → VAEDecode
```

### Key Considerations
- Pass 1 uses distilled LoRA for fast structure
- Pass 2 uses detailer LoRA for quality
- Different sigma schedules for each pass
- CFG=1 for distilled models

---

## 14. Subgraph Architecture

Modular workflow components with configurable inputs.

### When to Use
- Reusable pipeline components
- Complex workflows with repeated patterns
- Clean workflow organization

### Required Nodes
```
Subgraph node with proxy inputs/outputs
```

### Key Considerations
- Subgraphs encapsulate a group of nodes
- Expose configurable inputs (width, height, frame_count, fps)
- Can be reused across workflows
- Proxy widgets map external values to internal nodes

---

## 15. SetNode/GetNode Variables

Named variable system for complex graph routing.

### When to Use
- Reducing wire spaghetti
- Sharing values across distant nodes
- Complex workflows with many cross-connections

### Required Nodes
```
SetNode (store value with name) → GetNode (retrieve value by name)
```

### Key Considerations
- SetNode stores a value with a string name
- GetNode retrieves the value by name from anywhere in the graph
- One SetNode can feed multiple GetNodes
- Names must be unique within the workflow
- Reduces visual wire clutter dramatically

---

## 16. Anything Everywhere

Global broadcasting of values without explicit connections.

### When to Use
- Broadcasting CLIP or MODEL to many nodes
- Reducing repetitive connections
- Global configuration values

### Key Considerations
- Third-party node (cg-use-everywhere)
- Broadcasts values to all matching inputs
- Use sparingly to avoid confusion
- Good for CLIP, MODEL, VAE that feed many nodes

---

## 17. Manual Sigmas

Explicit sigma schedule as a string for precise control.

### When to Use
- Distilled models with specific schedules
- Custom step schedules
- Fine-tuned sampling behavior

### Required Nodes
```
ManualSigmas (sigmas_string="0.85,0.725,0.422,0.0") → SamplerCustomAdvanced
```

### Key Considerations
- Sigma values define noise levels at each step
- Must end with 0.0
- Descending order
- Distilled models use fewer steps (3-6)
- Base models use more steps (20-30)

---

## 18. NAG (Negative Guidance)

Enhanced negative prompting for LTX Video models.

### When to Use
- Stronger negative prompt influence
- LTX Video models
- Quality improvement through negative guidance

### Required Nodes
```
CLIPTextEncode (positive) → LTX2_NAG.positive
CLIPTextEncode (negative) → LTX2_NAG.negative
LTX2_NAG → SamplerCustomAdvanced
```

### Key Considerations
- nag_scale controls negative prompt strength (default 7.0)
- nag_tau controls guidance threshold (default 5.0)
- Higher nag_scale = stronger negative influence
- Only works with LTX2 models

---

## 19. Attention Optimization Chain

Stack multiple attention optimizations for maximum efficiency.

### When to Use
- Large models (22B+)
- Memory-constrained environments
- Long video generation

### Required Nodes
```
PathchSageAttentionKJ → LTX2MemoryEfficientSageAttentionPatch → LTXVChunkFeedForward → LTX2AttentionTunerPatch
```

### Key Considerations
- Each optimization reduces memory or increases speed
- Chain order matters
- Some optimizations are model-specific
- Test each individually before stacking

---

## 20. ControlNet Activation Detection

Automatically route based on whether ControlNet is connected.

### When to Use
- Optional ControlNet pipelines
- Toggle-able features
- Smart routing based on connections

### Required Nodes
```
ImpactIfNone → ComfySwitchNode → Pipeline A (with ControlNet) or Pipeline B (without)
```

### Key Considerations
- ImpactIfNone detects if a signal exists
- ComfySwitchNode routes based on boolean
- Enables optional ControlNet without manual switching
- Works with any optional input

---

## 21. ID LoRA Pipeline

Identity-preserving generation with activation toggle.

### When to Use
- Character consistency
- Face preservation
- Identity-aware generation

### Key Considerations
- ID LoRA preserves facial features
- Activation toggle enables/disables the effect
- ComfySwitchNode routes model through ID LoRA or bypass
- Can combine with ControlNet for full control

---

## 22. IC-LoRA Guidance

Image-Conditioning LoRA with latent downscale factor.

### When to Use
- Image-conditioned video generation
- Reference image guidance
- Style transfer with LoRA

### Key Considerations
- latent_downscale_factor controls guidance resolution (default 0.25)
- Lower factor = less VRAM but weaker guidance
- Higher factor = stronger guidance but more VRAM
- LTXAddVideoICLoRAGuide injects guidance into latent

---

## 23. GGUF Pipeline

Quantized model workflows for lower VRAM usage.

### When to Use
- Limited VRAM (8-12GB)
- Running large models on consumer hardware
- Acceptable quality trade-off for accessibility

### Key Considerations
- GGUF models are quantized (lossy compression)
- Lower quality than full precision
- Significantly less VRAM usage
- Same pipeline structure, different model files
- CheckpointLoaderSimple loads GGUF checkpoints

---

## 24. Dual Video Compare

Side-by-side video comparison with slider.

### When to Use
- Comparing before/after processing
- A/B testing different settings
- Quality comparison

### Required Nodes
```
DualVideoPreview (frames_1, frames_2, fps)
```

### Key Considerations
- Accepts file paths or frame tensors
- Slider-based comparison with synced playback
- Per-side audio muting
- Output-only terminal node

---

## Pattern Selection Guide

| Use Case | Recommended Pattern |
|---|---|
| Simple txt2img | Linear Pipeline |
| Style comparison | Branching Pipeline |
| High-res output | Multi-Pass Pipeline |
| Character consistency | Model Patching Chain |
| Animation | Video Pipeline |
| Precise control | ControlNet Stacking |
| Style transitions | Prompt Scheduling |
| Music visualization | Audio-Reactive |
| Conditional logic | Dynamic Processing |
| Bulk generation | Batch Processing |
| Audio-Video generation | Audio-Video Fusion |
| High-res video | Latent Upsampling |
| Distilled refinement | Two-Pass Sampling |
| Modular workflows | Subgraph Architecture |
| Complex routing | SetNode/GetNode Variables |
| Global broadcasting | Anything Everywhere |
| Precise sigma control | Manual Sigmas |
| Strong negative guidance | NAG |
| Memory optimization | Attention Optimization Chain |
| Optional features | ControlNet Activation Detection |
| Character consistency | ID LoRA Pipeline |
| Image-guided video | IC-LoRA Guidance |
| Low VRAM | GGUF Pipeline |
| A/B comparison | Dual Video Compare |

## Combining Patterns

Patterns can be combined for complex workflows:

```
Model Patching Chain + Multi-Pass:
  CheckpointLoader → LoRA → KSampler (pass1) → Upscale → LoRA → KSampler (pass2) → Save

Branching + ControlNet:
  Single loader → Branch A (with ControlNet depth) → Save
                → Branch B (with ControlNet pose) → Save

Video + Prompt Scheduling:
  AnimateDiff → KSampler (prompt changes per frame batch) → VideoCombine
```
