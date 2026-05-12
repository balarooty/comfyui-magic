# ComfyUI Node Catalog

Reference catalog of built-in and popular custom nodes. Each entry lists the exact node type name, display name, category, inputs, and outputs.

---

## Loaders

### CheckpointLoaderSimple

- **Display Name**: Load Checkpoint
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| ckpt_name | COMBO | — | Model filenames in `models/checkpoints/` |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Diffusion model |
| CLIP | CLIP | CLIP text encoder |
| VAE | VAE | VAE model |

---

### CheckpointLoader

- **Display Name**: Load Checkpoint (Advanced)
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| config_name | COMBO | — | Config file names |
| ckpt_name | COMBO | — | Model filenames |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Diffusion model |
| CLIP | CLIP | CLIP text encoder |
| VAE | VAE | VAE model |
| CLIP_VISION | CLIP_VISION | CLIP vision encoder |

---

### VAELoader

- **Display Name**: Load VAE
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| vae_name | COMBO | — | VAE filenames in `models/vae/` |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| VAE | VAE | VAE model |

---

### UNETLoader

- **Display Name**: UNET Loader (Advanced)
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| unet_name | COMBO | — | UNET filenames in `models/diffusion_models/` |
| weight_dtype | COMBO | "default" | "default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Diffusion model |

---

### DualCLIPLoader

- **Display Name**: Dual CLIP Loader
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| clip_name1 | COMBO | — | CLIP filenames |
| clip_name2 | COMBO | — | CLIP filenames |
| type | COMBO | "sdxl" | "sdxl", "sd3", "flux" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CLIP | CLIP | Combined CLIP encoder |

---

### TripleCLIPLoader

- **Display Name**: Triple CLIP Loader
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| clip_name1 | COMBO | — | CLIP filenames |
| clip_name2 | COMBO | — | CLIP filenames |
| clip_name3 | COMBO | — | CLIP filenames |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CLIP | CLIP | Combined CLIP encoder |

---

### LoraLoader

- **Display Name**: Load LoRA
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| clip | CLIP | — | (required) |
| lora_name | COMBO | — | LoRA filenames in `models/loras/` |
| strength_model | FLOAT | 1.0 | -10.0 to 10.0, step 0.01 |
| strength_clip | FLOAT | 1.0 | -10.0 to 10.0, step 0.01 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Patched model |
| CLIP | CLIP | Patched CLIP |

---

### LoraLoaderModelOnly

- **Display Name**: Load LoRA (Model Only)
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| lora_name | COMBO | — | LoRA filenames |
| strength_model | FLOAT | 1.0 | -10.0 to 10.0, step 0.01 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Patched model |

---

### ControlNetLoader

- **Display Name**: Load ControlNet Model
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| control_net_name | COMBO | — | ControlNet filenames in `models/controlnet/` |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONTROL_NET | CONTROL_NET | ControlNet model |

---

### IPAdapterModelLoader

- **Display Name**: Load IPAdapter Model
- **Category**: ipadapter

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| ipadapter_file | COMBO | — | IPAdapter filenames |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IPADAPTER | IPADAPTER_MODEL | IP-Adapter model |

---

### CLIPVisionLoader

- **Display Name**: Load CLIP Vision
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| clip_name | COMBO | — | CLIP vision filenames in `models/clip_vision/` |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CLIP_VISION | CLIP_VISION | CLIP vision model |

---

### StyleModelLoader

- **Display Name**: Load Style Model
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| style_model_name | COMBO | — | Style model filenames |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| STYLE_MODEL | STYLE_MODEL | Style model |

---

### LoaderDeprecated

- **Display Name**: Load Diffusion Model (Deprecated)
- **Category**: loaders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| ckpt_name | COMBO | — | Model filenames |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Diffusion model |
| CLIP | CLIP | CLIP encoder |
| VAE | VAE | VAE model |

---

## Sampling

### KSampler

- **Display Name**: KSampler
- **Category**: sampling

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| positive | CONDITIONING | — | (required) |
| negative | CONDITIONING | — | (required) |
| latent_image | LATENT | — | (required) |
| seed | INT | 0 | 0 to 2^32-1 |
| steps | INT | 20 | 1 to 10000 |
| cfg | FLOAT | 8.0 | 0.0 to 100.0 |
| sampler_name | COMBO | "euler" | "euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_sde", "dpmpp_sde_gpu", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu", "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm", "ddim", "uni_pc", "uni_pc_bh2" |
| scheduler | COMBO | "normal" | "normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform", "beta" |
| denoise | FLOAT | 1.0 | 0.0 to 1.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Sampled latent |

---

### KSamplerAdvanced

- **Display Name**: KSampler (Advanced)
- **Category**: sampling

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| positive | CONDITIONING | — | (required) |
| negative | CONDITIONING | — | (required) |
| latent_image | LATENT | — | (required) |
| noise_seed | INT | 0 | 0 to 2^32-1 |
| steps | INT | 20 | 1 to 10000 |
| cfg | FLOAT | 8.0 | 0.0 to 100.0 |
| sampler_name | COMBO | "euler" | (same as KSampler) |
| scheduler | COMBO | "normal" | (same as KSampler) |
| start_at_step | INT | 0 | 0 to 10000 |
| end_at_step | INT | 10000 | 0 to 10000 |
| return_with_leftover_noise | COMBO | "disable" | "enable", "disable" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Sampled latent |

---

### SamplerCustom

- **Display Name**: SamplerCustom
- **Category**: sampling

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| add_noise | BOOLEAN | true | — |
| noise_seed | INT | 0 | 0 to 2^32-1 |
| cfg | FLOAT | 8.0 | 0.0 to 100.0 |
| positive | CONDITIONING | — | (required) |
| negative | CONDITIONING | — | (required) |
| sampler | SAMPLER | — | (required) |
| sigmas | SIGMAS | — | (required) |
| latent_image | LATENT | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| output | LATENT | Sampled latent |
| denoised_output | LATENT | Denoised latent |

---

### BasicGuider

- **Display Name**: BasicGuider
- **Category**: sampling/guiders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| conditioning | CONDITIONING | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| GUIDER | GUIDER | Guider object |

---

### CFGGuider

- **Display Name**: CFGGuider
- **Category**: sampling/guiders

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| positive | CONDITIONING | — | (required) |
| negative | CONDITIONING | — | (required) |
| cfg | FLOAT | 8.0 | 0.0 to 100.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| GUIDER | GUIDER | Guider object |

---

### BasicScheduler

- **Display Name**: BasicScheduler
- **Category**: sampling/schedulers

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| scheduler | COMBO | "normal" | "normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform", "beta" |
| steps | INT | 20 | 1 to 10000 |
| denoise | FLOAT | 1.0 | 0.0 to 1.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| SIGMAS | SIGMAS | Sigma schedule |

---

### KSamplerSelect

- **Display Name**: KSamplerSelect
- **Category**: sampling/samplers

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| sampler_name | COMBO | "euler" | (same as KSampler sampler options) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| SAMPLER | SAMPLER | Sampler object |

---

### ModelSamplingDiscrete

- **Display Name**: ModelSamplingDiscrete
- **Category**: sampling

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| sampling | COMBO | "eps" | "eps", "v_prediction", "lcm", "x0" |
| zsnr | BOOLEAN | false | — |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Modified model |

---

### ModelSamplingFlux

- **Display Name**: ModelSamplingFlux
- **Category**: sampling

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| model | MODEL | — | (required) |
| max_shift | FLOAT | 1.15 | 0.0 to 100.0 |
| base_shift | FLOAT | 0.5 | 0.0 to 100.0 |
| width | INT | 1024 | 16 to 16384 |
| height | INT | 1024 | 16 to 16384 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Model with Flux sampling |

---

## Latent

### EmptyLatentImage

- **Display Name**: Empty Latent Image
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| width | INT | 512 | 16 to 16384 |
| height | INT | 512 | 16 to 16384 |
| batch_size | INT | 1 | 1 to 4096 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Empty latent tensor |

---

### LatentUpscale

- **Display Name**: Latent Upscale
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| samples | LATENT | — | (required) |
| upscale_method | COMBO | "nearest-exact" | "nearest-exact", "bilinear", "area", "bislerp" |
| width | INT | 512 | 16 to 16384 |
| height | INT | 512 | 16 to 16384 |
| crop | COMBO | "disabled" | "disabled", "center" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Upscaled latent |

---

### LatentBatch

- **Display Name**: Latent Batch
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| samples1 | LATENT | — | (required) |
| samples2 | LATENT | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Batched latent |

---

### LatentRotate

- **Display Name**: Latent Rotate
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| samples | LATENT | — | (required) |
| rotation | COMBO | "none" | "none", "90 degrees", "180 degrees", "270 degrees", "90 degrees mirror", "180 degrees mirror", "270 degrees mirror" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Rotated latent |

---

### LatentFlip

- **Display Name**: Latent Flip
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| samples | LATENT | — | (required) |
| flip_method | COMBO | "x-axis: vertically" | "x-axis: vertically", "y-axis: horizontally", "x-y-axis: x=y" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Flipped latent |

---

### LatentCrop

- **Display Name**: Latent Crop
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| samples | LATENT | — | (required) |
| width | INT | 512 | 16 to 16384 |
| height | INT | 512 | 16 to 16384 |
| x | INT | 0 | 0 to 16384 |
| y | INT | 0 | 0 to 16384 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Cropped latent |

---

## VAE

### VAEDecode

- **Display Name**: VAE Decode
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| samples | LATENT | — | (required) |
| vae | VAE | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Decoded image(s) |

---

### VAEEncode

- **Display Name**: VAE Encode
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| pixels | IMAGE | — | (required) |
| vae | VAE | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Encoded latent |

---

### VAEDecodeTiled

- **Display Name**: VAE Decode (Tiled)
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| samples | LATENT | — | (required) |
| vae | VAE | — | (required) |
| tile_size | INT | 512 | 64 to 4096 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Decoded image(s) |

---

### VAEEncodeTiled

- **Display Name**: VAE Encode (Tiled)
- **Category**: latent

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| pixels | IMAGE | — | (required) |
| vae | VAE | — | (required) |
| tile_size | INT | 512 | 64 to 4096 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Encoded latent |

---

## Conditioning

### CLIPTextEncode

- **Display Name**: CLIP Text Encode
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| text | STRING | "" | multiline |
| clip | CLIP | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Text conditioning |

---

### ConditioningCombine

- **Display Name**: Conditioning Combine
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| conditioning_1 | CONDITIONING | — | (required) |
| conditioning_2 | CONDITIONING | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Combined conditioning |

---

### ConditioningConcat

- **Display Name**: Conditioning Concat
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| conditioning_to | CONDITIONING | — | (required) |
| conditioning_from | CONDITIONING | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Concatenated conditioning |

---

### ConditioningSetArea

- **Display Name**: Conditioning Set Area
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| conditioning | CONDITIONING | — | (required) |
| width | INT | 512 | 16 to 16384 |
| height | INT | 512 | 16 to 16384 |
| x | INT | 0 | 0 to 16384 |
| y | INT | 0 | 0 to 16384 |
| strength | FLOAT | 1.0 | 0.0 to 10.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Area-conditioned output |

---

### ConditioningSetMask

- **Display Name**: Conditioning Set Mask
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| conditioning | CONDITIONING | — | (required) |
| mask | MASK | — | (required) |
| strength | FLOAT | 1.0 | 0.0 to 10.0 |
| set_cond_area | COMBO | "default" | "default", "mask bounds" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Mask-conditioned output |

---

### CLIPSetLastLayer

- **Display Name**: CLIP Set Last Layer
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| clip | CLIP | — | (required) |
| stop_at_clip_layer | INT | -1 | -1 to -24 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CLIP | CLIP | Modified CLIP |

---

### ControlNetApply

- **Display Name**: Apply ControlNet
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| conditioning | CONDITIONING | — | (required) |
| control_net | CONTROL_NET | — | (required) |
| image | IMAGE | — | (required) |
| strength | FLOAT | 1.0 | 0.0 to 10.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | ControlNet-conditioned output |

---

### ControlNetApplyAdvanced

- **Display Name**: Apply ControlNet (Advanced)
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| positive | CONDITIONING | — | (required) |
| negative | CONDITIONING | — | (required) |
| control_net | CONTROL_NET | — | (required) |
| image | IMAGE | — | (required) |
| strength | FLOAT | 1.0 | 0.0 to 10.0 |
| start_percent | FLOAT | 0.0 | 0.0 to 1.0 |
| end_percent | FLOAT | 1.0 | 0.0 to 1.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| positive | CONDITIONING | Positive with ControlNet |
| negative | CONDITIONING | Negative with ControlNet |

---

## Image

### SaveImage

- **Display Name**: Save Image
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| images | IMAGE | — | (required) |
| filename_prefix | STRING | "ComfyUI" | — |

**Outputs**: None (terminal node)

---

### PreviewImage

- **Display Name**: Preview Image
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| images | IMAGE | — | (required) |

**Outputs**: None (terminal node)

---

### LoadImage

- **Display Name**: Load Image
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| image | COMBO | — | Image filenames in `input/` |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Loaded image |
| MASK | MASK | Alpha mask from image |

---

### ImageScale

- **Display Name**: Image Scale
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| image | IMAGE | — | (required) |
| upscale_method | COMBO | "nearest-exact" | "nearest-exact", "bilinear", "area", "bislerp", "lanczos" |
| width | INT | 512 | 1 to 16384 |
| height | INT | 512 | 1 to 16384 |
| crop | COMBO | "disabled" | "disabled", "center" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Scaled image |

---

### ImageScaleBy

- **Display Name**: Image Scale By
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| image | IMAGE | — | (required) |
| upscale_method | COMBO | "nearest-exact" | "nearest-exact", "bilinear", "area", "bislerp", "lanczos" |
| scale_by | FLOAT | 1.0 | 0.01 to 8.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Scaled image |

---

### ImageInvert

- **Display Name**: Image Invert
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| image | IMAGE | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Inverted image |

---

### ImageBatch

- **Display Name**: Image Batch
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| image1 | IMAGE | — | (required) |
| image2 | IMAGE | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Batched images |

---

### ImagePadForOutpaint

- **Display Name**: Pad Image for Outpainting
- **Category**: image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| image | IMAGE | — | (required) |
| left | INT | 0 | 0 to 16384 |
| top | INT | 0 | 0 to 16384 |
| right | INT | 0 | 0 to 16384 |
| bottom | INT | 0 | 0 to 16384 |
| feathering | INT | 40 | 0 to 16384 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Padded image |
| MASK | MASK | Padding mask |

---

## Mask

### EmptyMask

- **Display Name**: Empty Mask
- **Category**: mask

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| width | INT | 512 | 16 to 16384 |
| height | INT | 512 | 16 to 16384 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MASK | MASK | Empty (zero) mask |

---

### MaskToImage

- **Display Name**: Convert Mask to Image
- **Category**: mask

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| mask | MASK | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Mask as grayscale image |

---

### ImageToMask

- **Display Name**: Convert Image to Mask
- **Category**: mask

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| image | IMAGE | — | (required) |
| channel | COMBO | "alpha" | "alpha", "red", "green", "blue" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MASK | MASK | Extracted mask |

---

### MaskComposite

- **Display Name**: Mask Composite
- **Category**: mask

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| destination | MASK | — | (required) |
| source | MASK | — | (required) |
| x | INT | 0 | 0 to 16384 |
| y | INT | 0 | 0 to 16384 |
| operation | COMBO | "multiply" | "multiply", "add", "subtract", "lightest", "darkest" |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MASK | MASK | Composited mask |

---

### MaskBatch

- **Display Name**: Mask Batch
- **Category**: mask

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| mask1 | MASK | — | (required) |
| mask2 | MASK | — | (required) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MASK | MASK | Batched masks |

---

## Video (VHS - Video Helper Suite)

### VHS_VideoCombine

- **Display Name**: Video Combine
- **Category**: video

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| images | IMAGE | — | (required) |
| frame_rate | INT | 8 | 1 to 120 |
| loop_count | INT | 0 | 0 to 100 |
| filename_prefix | STRING | "AnimateDiff" | — |
| format | COMBO | "image/gif" | "image/gif", "image/webp", "image/apng", "video/h264-mp4", "video/h265-mp4", "video/webm" |
| pingpong | BOOLEAN | false | — |
| save_output | BOOLEAN | true | — |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| VHS_FILENAMES | VHS_FILENAMES | Output file info |

---

### VHS_LoadVideo

- **Display Name**: Load Video
- **Category**: video

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| video | COMBO | — | Video filenames in `input/` |
| force_rate | INT | 0 | 0 to 120 |
| force_size | COMBO | "Disabled" | "Disabled", "256x?", "?x256", "256x256", "512x?", "?x512", "512x512" |
| custom_width | INT | 512 | 0 to 16384 |
| custom_height | INT | 512 | 0 to 16384 |
| frame_load_cap | INT | 0 | 0 to 10000 |
| skip_first_frames | INT | 0 | 0 to 10000 |
| select_every_nth | INT | 1 | 1 to 100 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Video frames as images |
| frame_rate | FLOAT | Detected frame rate |
| duration | FLOAT | Video duration in seconds |

---

### VHS_LoadVideoPath

- **Display Name**: Load Video (Path)
- **Category**: video

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| video | STRING | "" | file path |
| force_rate | INT | 0 | 0 to 120 |
| force_size | COMBO | "Disabled" | (same as VHS_LoadVideo) |
| custom_width | INT | 512 | 0 to 16384 |
| custom_height | INT | 512 | 0 to 16384 |
| frame_load_cap | INT | 0 | 0 to 10000 |
| skip_first_frames | INT | 0 | 0 to 10000 |
| select_every_nth | INT | 1 | 1 to 100 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Video frames as images |
| frame_rate | FLOAT | Detected frame rate |
| duration | FLOAT | Video duration in seconds |

---

## KJNodes

### ImageConcatMulti

- **Display Name**: Image Concat Multi
- **Category**: KJNodes/image

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| images_* | IMAGE | — | Dynamic inputs (auto-generated) |
| axis | COMBO | "horizontal" | "horizontal", "vertical" |
| match_size | BOOLEAN | false | — |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Concatenated image |

---

### ConditioningMultiCombine

- **Display Name**: Conditioning Multi Combine
- **Category**: KJNodes/conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| conditioning_* | CONDITIONING | — | Dynamic inputs (auto-generated) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Combined conditioning |

---

### MaskBatchMulti

- **Display Name**: Mask Batch Multi
- **Category**: KJNodes/mask

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| mask_* | MASK | — | Dynamic inputs (auto-generated) |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| MASK | MASK | Batched masks |

---

### INTConstant

- **Display Name**: INT Constant
- **Category**: KJNodes/constants

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| value | INT | 0 | — |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| INT | INT | Integer value |

---

### FLOATConstant

- **Display Name**: FLOAT Constant
- **Category**: KJNodes/constants

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| value | FLOAT | 0.0 | — |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| FLOAT | FLOAT | Float value |

---

### STRINGConstant

- **Display Name**: STRING Constant
- **Category**: KJNodes/constants

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| value | STRING | "" | — |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| STRING | STRING | String value |

---

### BoolConstant

- **Display Name**: Bool Constant
- **Category**: KJNodes/constants

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| value | BOOLEAN | false | — |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| BOOLEAN | BOOLEAN | Boolean value |

---

## Flux-Specific

### CLIPTextEncodeFlux

- **Display Name**: CLIP Text Encode (Flux)
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| clip | CLIP | — | (required) |
| clip_l | STRING | "" | multiline |
| t5xxl | STRING | "" | multiline |
| guidance | FLOAT | 3.5 | 0.0 to 100.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Flux conditioning |

---

### FluxGuidance

- **Display Name**: Flux Guidance
- **Category**: conditioning

**Inputs**:
| Name | Type | Default | Options |
|---|---|---|---|
| conditioning | CONDITIONING | — | (required) |
| guidance | FLOAT | 3.5 | 0.0 to 100.0 |

**Outputs**:
| Name | Type | Description |
|---|---|---|
| CONDITIONING | CONDITIONING | Conditioning with guidance |

---

## LTX Video Nodes

### LTXVLoader

- **Display Name**: LTX Video Loader
- **Category**: loaders

**Inputs**: ckpt_name (COMBO), text_encoder_name (COMBO), vae_name (COMBO)
**Outputs**: MODEL, CLIP, VAE

### LTXVImgToVideoInplace

- **Display Name**: LTX Image to Video (Inplace)
- **Category**: LTXV

**Inputs**: model (MODEL), vae (VAE), image (IMAGE), width (INT, 480), height (INT, 256), frame_count (INT, 97), batch_size (INT, 1)
**Outputs**: LATENT

### LTXVImgToVideoConditionOnly

- **Display Name**: LTX Image to Video (Condition Only)
- **Category**: LTXV

**Inputs**: conditioning (CONDITIONING), image (IMAGE), vae (VAE), strength (FLOAT, 0.15)
**Outputs**: CONDITIONING

### LTXVAddGuide

- **Display Name**: LTX Add Guide (Single)
- **Category**: LTXV

**Inputs**: latent (LATENT), image (IMAGE), strength (FLOAT, 1.0), timestep (FLOAT, 0.0)
**Outputs**: LATENT

### LTXVAddGuideMulti

- **Display Name**: LTX Add Guide (Multi)
- **Category**: LTXV

**Inputs**: latent (LATENT), images (IMAGE, multiple), strengths (FLOAT), timesteps (FLOAT)
**Outputs**: LATENT

### LTXVConditioning

- **Display Name**: LTX Conditioning
- **Category**: LTXV

**Inputs**: positive (CONDITIONING), frame_rate (INT, 24)
**Outputs**: CONDITIONING

### LTXVScheduler

- **Display Name**: LTX Scheduler
- **Category**: LTXV

**Inputs**: model (MODEL), steps (INT, 20), max_shift (FLOAT, 2.05), base_shift (FLOAT, 0.95), stretch (BOOLEAN, true), terminal (FLOAT, 0.1)
**Outputs**: SIGMAS

### LTXVLatentUpsampler

- **Display Name**: LTX Latent Upsampler
- **Category**: LTXV

**Inputs**: model (MODEL), latent (LATENT), upscale_model (UPSCALE_MODEL)
**Outputs**: LATENT

### LTXVConcatAVLatent

- **Display Name**: LTX Concat AV Latent
- **Category**: LTXV

**Inputs**: video_latent (LATENT), audio_latent (LATENT)
**Outputs**: LATENT

### LTXVSeparateAVLatent

- **Display Name**: LTX Separate AV Latent
- **Category**: LTXV

**Inputs**: latent (LATENT), frame_count (INT)
**Outputs**: video_latent (LATENT), audio_latent (LATENT)

### LTXVAudioVAELoader

- **Display Name**: LTX Audio VAE Loader
- **Category**: loaders

**Inputs**: ckpt_name (COMBO)
**Outputs**: VAE

### LTXVAudioVAEDecode

- **Display Name**: LTX Audio VAE Decode
- **Category**: LTXV

**Inputs**: samples (LATENT), vae (VAE), frame_rate (INT, 24)
**Outputs**: AUDIO

### LTXVAudioVAEEncode

- **Display Name**: LTX Audio VAE Encode
- **Category**: LTXV

**Inputs**: audio (AUDIO), vae (VAE), frame_rate (INT, 24)
**Outputs**: LATENT

### LTXVEmptyLatentAudio

- **Display Name**: LTX Empty Latent Audio
- **Category**: LTXV

**Inputs**: frame_count (INT, 97), frame_rate (INT, 24)
**Outputs**: LATENT

### LTXVSpatioTemporalTiledVAEDecode

- **Display Name**: LTX Spatio Temporal Tiled VAE Decode
- **Category**: LTXV

**Inputs**: samples (LATENT), vae (VAE), tile_size_x (INT, 4), tile_size_y (INT, 4), tile_size_t (INT, 16)
**Outputs**: IMAGE

### LTXVPreprocess

- **Display Name**: LTX Preprocess
- **Category**: LTXV

**Inputs**: image (IMAGE), img_compression (INT, 18)
**Outputs**: IMAGE

### LTXVCropGuides

- **Display Name**: LTX Crop Guides
- **Category**: LTXV

**Inputs**: latent (LATENT), guides (LATENT)
**Outputs**: LATENT

### LTXVChunkFeedForward

- **Display Name**: LTX Chunk Feed Forward
- **Category**: LTXV

**Inputs**: model (MODEL), chunk_size (INT, 8192)
**Outputs**: MODEL

### LTX2_NAG

- **Display Name**: LTX2 NAG (Negative Guidance)
- **Category**: LTXV

**Inputs**: positive (CONDITIONING), negative (CONDITIONING), nag_scale (FLOAT, 7.0), nag_tau (FLOAT, 5.0)
**Outputs**: CONDITIONING

### LTX2AttentionTunerPatch

- **Display Name**: LTX2 Attention Tuner
- **Category**: LTXV

**Inputs**: model (MODEL), tuner_strength (FLOAT, 1.0)
**Outputs**: MODEL

### LTX2MemoryEfficientSageAttentionPatch

- **Display Name**: LTX2 Memory Efficient Sage Attention
- **Category**: LTXV

**Inputs**: model (MODEL)
**Outputs**: MODEL

### LTX2SamplingPreviewOverride

- **Display Name**: LTX2 Sampling Preview Override
- **Category**: LTXV

**Inputs**: model (MODEL), vae (VAE), preview_interval (INT, 5)
**Outputs**: MODEL

---

## KJNodes Advanced

### SetNode

- **Display Name**: Set Node (Variable)
- **Category**: KJNodes/variables

**Inputs**: value (*), name (STRING)
**Outputs**: *

### GetNode

- **Display Name**: Get Node (Variable)
- **Category**: KJNodes/variables

**Inputs**: name (STRING)
**Outputs**: *

### PathchSageAttentionKJ

- **Display Name**: Patch Sage Attention
- **Category**: KJNodes/optimization

**Inputs**: model (MODEL)
**Outputs**: MODEL

### ManualSigmas

- **Display Name**: Manual Sigmas
- **Category**: KJNodes/sampling

**Inputs**: sigmas_string (STRING), model (MODEL)
**Outputs**: SIGMAS

### ImageResizeKJv2

- **Display Name**: Image Resize KJ v2
- **Category**: KJNodes/image

**Inputs**: image (IMAGE), width (INT, 512), height (INT, 512), upscale_method (COMBO), crop (COMBO)
**Outputs**: IMAGE

### ResizeImagesByLongerEdge

- **Display Name**: Resize by Longer Edge
- **Category**: KJNodes/image

**Inputs**: images (IMAGE), size (INT, 1536), interpolation (COMBO)
**Outputs**: IMAGE

### MultiplyNode

- **Display Name**: Multiply
- **Category**: KJNodes/math

**Inputs**: a (FLOAT), b (FLOAT)
**Outputs**: FLOAT

### MarkdownNote

- **Display Name**: Markdown Note
- **Category**: KJNodes/utility

**Inputs**: text (STRING, multiline)
**Outputs**: (none - display only)

---

## Rogala Nodes

### SamplerSchedulerIterator

- **Display Name**: Sampler Scheduler Iterator
- **Category**: rogala/Samplers

**Inputs**: sampler_list (STRING), scheduler_list (STRING), seed (INT)
**Outputs**: SAMPLER, STRING, STRING, INT

### AlignedTextOverlayImages

- **Display Name**: Aligned Text Overlay (Images)
- **Category**: rogala/Image

**Inputs**: images (IMAGE), text (STRING), font_size (INT, 24), position (COMBO), color (STRING)
**Outputs**: IMAGE

### AlignedTextOverlayVideo

- **Display Name**: Aligned Text Overlay (Video)
- **Category**: rogala/Video

**Inputs**: images (IMAGE), text (STRING), font_size (INT, 24), position (COMBO), color (STRING)
**Outputs**: IMAGE

### LtxResolutionSelector

- **Display Name**: LTX Resolution Selector
- **Category**: rogala/Video

**Inputs**: resolution_preset (COMBO), frame_count (INT)
**Outputs**: INT, INT, INT

### FmlfLtx23

- **Display Name**: FML LTX 2.3 (First-Middle-Last)
- **Category**: rogala/Video

**Inputs**: model (MODEL), images (IMAGE, up to 6), frame_count (INT), resolution (COMBO)
**Outputs**: LATENT, CONDITIONING

### SamplerLtxv23

- **Display Name**: Sampler LTX v2.3 (Two-Pass)
- **Category**: rogala/Video

**Inputs**: model (MODEL), latent (LATENT), positive (CONDITIONING), negative (CONDITIONING), seed (INT), steps (INT), upscale_model (UPSCALE_MODEL)
**Outputs**: LATENT

### AdvancedStyleSelector

- **Display Name**: Advanced Style Selector
- **Category**: rogala/Prompting

**Inputs**: style_names (STRING, multiple), num_styles (INT), model (MODEL), clip (CLIP)
**Outputs**: CONDITIONING

### SmartAttentionDispatcher

- **Display Name**: Smart Attention Dispatcher
- **Category**: rogala/Optimization

**Inputs**: model (MODEL), mode (COMBO: auto/sa2/sa3/sdpa/dynamic)
**Outputs**: MODEL

---

## DualVideoCompare

### DualVideoPreview

- **Display Name**: Dual Video Preview
- **Category**: image/video

**Inputs**: video_1 (STRING, optional), video_2 (STRING, optional), frames_1 (IMAGE, optional), frames_2 (IMAGE, optional), audio_1 (AUDIO, optional), audio_2 (AUDIO, optional), label_1 (STRING, "Before"), label_2 (STRING, "After"), fps (INT, 24), loop (BOOLEAN, true)
**Outputs**: (none - terminal node, OUTPUT_NODE=True)

---

## Sampling Advanced

### SamplerCustomAdvanced

- **Display Name**: Sampler Custom Advanced
- **Category**: sampling

**Inputs**: noise (NOISE), guider (GUIDER), sampler (SAMPLER), sigmas (SIGMAS), latent_image (LATENT)
**Outputs**: output (LATENT), denoised_output (LATENT)

### RandomNoise

- **Display Name**: Random Noise
- **Category**: sampling

**Inputs**: noise_seed (INT)
**Outputs**: NOISE

---

## Node Type Quick Reference

| Category | Node Type | Key Outputs |
|---|---|---|
| Loaders | CheckpointLoaderSimple | MODEL, CLIP, VAE |
| Loaders | UNETLoader | MODEL |
| Loaders | LoraLoader | MODEL, CLIP |
| Loaders | ControlNetLoader | CONTROL_NET |
| Loaders | CLIPVisionLoader | CLIP_VISION |
| Sampling | KSampler | LATENT |
| Sampling | SamplerCustom | LATENT |
| Sampling | BasicGuider | GUIDER |
| Sampling | BasicScheduler | SIGMAS |
| Latent | EmptyLatentImage | LATENT |
| Latent | LatentUpscale | LATENT |
| VAE | VAEDecode | IMAGE |
| VAE | VAEEncode | LATENT |
| Conditioning | CLIPTextEncode | CONDITIONING |
| Conditioning | ControlNetApply | CONDITIONING |
| Image | SaveImage | (none) |
| Image | LoadImage | IMAGE, MASK |
| Image | ImageScale | IMAGE |
| Mask | EmptyMask | MASK |
| Mask | MaskToImage | IMAGE |
| Video | VHS_VideoCombine | VHS_FILENAMES |
| Video | VHS_LoadVideo | IMAGE |
| Flux | CLIPTextEncodeFlux | CONDITIONING |
| Flux | FluxGuidance | CONDITIONING |
| Loaders | LTXVLoader | MODEL, CLIP, VAE |
| LTXV | LTXVImgToVideoInplace | LATENT |
| LTXV | LTXVConcatAVLatent | LATENT |
| LTXV | LTXVSeparateAVLatent | LATENT |
| LTXV | LTXVAudioVAEDecode | AUDIO |
| LTXV | LTX2_NAG | CONDITIONING |
| KJNodes | SetNode | * |
| KJNodes | GetNode | * |
| KJNodes | ManualSigmas | SIGMAS |
| Sampling | SamplerCustomAdvanced | LATENT |
| Sampling | RandomNoise | NOISE |
| Image | DualVideoPreview | (none) |
