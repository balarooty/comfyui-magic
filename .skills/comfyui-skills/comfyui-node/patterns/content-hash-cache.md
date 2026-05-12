# Content-Hash Cache

## When to Use

- Expensive operations (video encoding, upscaling, rendering) where identical inputs should produce identical outputs without reprocessing
- Replacing fragile timestamp-based caching with deterministic, content-aware caching
- Workflow re-runs where the user expects instant results for unchanged inputs
- Long-running output nodes where skipping redundant work saves minutes

## Pattern

Hash representative frame pixels (first, middle, last) with MD5. Use the hash as the output filename. If the file already exists, return it immediately.

```python
import os
import hashlib
import numpy as np
from PIL import Image

import folder_paths


class CachedImageUpscaler:
    """Upscales images with content-hash caching — skips if output already exists."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "scale_factor": ("INT", {"default": 2, "min": 1, "max": 8}),
                "method": (["nearest", "bilinear", "bicubic", "lanczos"], {
                    "default": "lanczos",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("upscaled", "output_path")
    FUNCTION = "upscale"
    CATEGORY = "image"
    OUTPUT_NODE = True

    METHOD_MAP = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
        "lanczos": Image.LANCZOS,
    }

    def _compute_hash(self, images_tensor, scale_factor, method):
        """Content-aware hash: pixel data + processing parameters."""
        h = hashlib.md5()

        n = images_tensor.shape[0]
        # Sample frames: first, middle, last
        sample_indices = sorted(set([0, n // 2, max(0, n - 1)]))
        for idx in sample_indices:
            frame = (255.0 * images_tensor[idx].cpu().numpy()).astype(np.uint8)
            h.update(frame.tobytes())

        # Include processing params so different settings = different cache
        h.update(f"scale={scale_factor}".encode())
        h.update(f"method={method}".encode())

        return h.hexdigest()[:16]

    def _get_cache_path(self, content_hash, image_index):
        output_dir = folder_paths.get_output_directory()
        cache_dir = os.path.join(output_dir, "upscale_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{content_hash}_{image_index:04d}.png")

    def upscale(self, images, scale_factor=2, method="lanczos"):
        content_hash = self._compute_hash(images, scale_factor, method)
        pil_method = self.METHOD_MAP[method]

        output_dir = folder_paths.get_output_directory()
        cache_dir = os.path.join(output_dir, "upscale_cache")
        os.makedirs(cache_dir, exist_ok=True)

        upscaled_frames = []
        output_paths = []
        cache_hits = 0
        cache_misses = 0

        for i in range(images.shape[0]):
            cache_path = self._get_cache_path(content_hash, i)

            if os.path.exists(cache_path):
                # Cache hit — load from disk
                cached_img = Image.open(cache_path)
                frame_np = np.array(cached_img).astype(np.float32) / 255.0
                cache_hits += 1
            else:
                # Cache miss — upscale and save
                frame_np = (255.0 * images[i].cpu().numpy()).astype(np.uint8)
                pil_img = Image.fromarray(frame_np)
                w, h = pil_img.size
                upscaled_img = pil_img.resize(
                    (w * scale_factor, h * scale_factor),
                    pil_method,
                )
                upscaled_img.save(cache_path, "PNG")
                frame_np = np.array(upscaled_img).astype(np.float32) / 255.0
                cache_misses += 1

            upscaled_frames.append(frame_np)
            output_paths.append(cache_path)

        # Reconstruct tensor
        result_tensor = np.stack(upscaled_frames, axis=0)

        import torch
        result_tensor = torch.from_numpy(result_tensor).float()

        summary = (
            f"Cache: {cache_hits} hits, {cache_misses} misses | "
            f"Hash: {content_hash} | "
            f"{images.shape[0]} frames @ {scale_factor}x"
        )

        return (result_tensor, summary)


NODE_CLASS_MAPPINGS = {
    "CachedImageUpscaler": CachedImageUpscaler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CachedImageUpscaler": "Cached Image Upscaler",
}
```

## Key Considerations

- **Hash a subset of frames**, not all. Sampling first/middle/last gives good collision resistance at O(1) cost vs O(n) for full-frame hashing.
- **Include processing parameters** in the hash. Same pixels with different scale or method must produce different cache keys.
- **MD5 is fine for caching** — collision resistance is not a security concern here; speed matters more than cryptographic strength.
- **Filename-based cache** is simpler than a database. The hash becomes the filename, making cache invalidation trivial (delete the file).
- **Store cache in the output directory** so it survives across sessions. Use a dedicated subdirectory to avoid cluttering the main output folder.
- **Cache hits bypass the GPU entirely** — no tensor processing, just disk I/O. This is the main performance win.
- **Don't cache intermediate tensors** — cache final output files. Intermediate caching requires managing the execution engine's lifecycle.
- **HDD vs SSD matters.** Random reads from hundreds of small PNGs will be slow on spinning disks. Consider a single-file archive format for HDD-heavy workflows.
- If you need cache eviction, sort files by access time and delete the oldest N when the cache exceeds a size limit.
