# Parallel Encoding

## When to Use

- Writing many images or frames to disk where sequential I/O is the bottleneck
- Encoding image sequences to video via ffmpeg while the next batch starts processing
- Any CPU-bound post-processing that benefits from multiple cores
- Dual-track workflows (e.g., preview + final) that can run concurrently

## Pattern

Use `concurrent.futures.ThreadPoolExecutor` to parallelize I/O-bound work (PNG writes, ffmpeg encoding). Combine with content-hash caching to skip redundant work.

```python
import os
import hashlib
import subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

import folder_paths


class DualVideoEncoder:
    """Encodes image sequences to MP4 using parallel PNG writes and ffmpeg."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "video"}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    FUNCTION = "encode"
    CATEGORY = "output"
    OUTPUT_NODE = True

    def _content_hash(self, images_tensor):
        """Hash first, middle, and last frame pixels."""
        n = images_tensor.shape[0]
        indices = [0, n // 2, n - 1]
        h = hashlib.md5()
        for idx in indices:
            frame = (255.0 * images_tensor[idx].cpu().numpy()).astype(np.uint8)
            h.update(frame.tobytes())
        return h.hexdigest()[:12]

    def _write_png(self, frame_np, path):
        """Write a single numpy frame as PNG."""
        Image.fromarray(frame_np).save(path, "PNG")
        return path

    def encode(self, images, filename_prefix="video", fps=24):
        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)

        # Content-hash based caching
        content_hash = self._content_hash(images)
        frame_dir = os.path.join(output_dir, f"{filename_prefix}_{content_hash}")
        video_path = os.path.join(output_dir, f"{filename_prefix}_{content_hash}.mp4")

        # Skip if already encoded
        if os.path.exists(video_path):
            return (video_path,)

        os.makedirs(frame_dir, exist_ok=True)

        num_frames = images.shape[0]

        # Phase 1: Parallel PNG writes
        frame_paths = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {}
            for i in range(num_frames):
                frame_np = (255.0 * images[i].cpu().numpy()).astype(np.uint8)
                frame_path = os.path.join(frame_dir, f"frame_{i:06d}.png")
                f = pool.submit(self._write_png, frame_np, frame_path)
                futures[f] = i

            for future in as_completed(futures):
                future.result()  # propagate exceptions
                frame_paths.append(futures[future])

        # Phase 2: ffmpeg encode image sequence to mp4
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(frame_dir, "frame_%06d.png"),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            video_path,
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        return (video_path,)


NODE_CLASS_MAPPINGS = {
    "DualVideoEncoder": DualVideoEncoder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DualVideoEncoder": "Dual Video Encoder",
}
```

## Key Considerations

- `ThreadPoolExecutor` is ideal for I/O-bound work (disk writes, subprocess calls). Use `ProcessExecutor` only for heavy CPU math — the GIL limits threading for pure Python compute.
- Tune `max_workers` to the number of physical cores or disk throughput. 8 is a sensible default for NVMe SSDs; reduce for HDDs.
- Always call `future.result()` inside `as_completed` to propagate exceptions. Silent failures are hard to debug.
- `subprocess.run(..., check=True, capture_output=True)` raises `CalledProcessError` on ffmpeg failure instead of silently producing a corrupt file.
- Content-hash caching prevents re-encoding identical frames. Hash a subset of frames (first, middle, last) for speed; full-frame hashing defeats the purpose.
- Clean up the temporary frame directory after encoding if disk space is a concern.
- The `-y` flag to ffmpeg overwrites without prompting — safe for automated pipelines.
- `-pix_fmt yuv420p` ensures compatibility with most video players and browsers.
