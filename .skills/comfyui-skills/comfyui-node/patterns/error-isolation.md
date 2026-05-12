# Error Isolation: try/except Import Pattern

## When to Use

Use this pattern when your node **depends on an optional package** that may not be installed. Common cases:

- A node that uses `scipy`, `open3d`, `trimesh`, or other heavy scientific libraries
- A node that uses a GPU-specific library (`xformers`, `triton`) not available on all systems
- A node that uses a proprietary SDK (`replicate`, `stability-sdk`)
- Any dependency that should not block the rest of your node pack from loading

Without this pattern, a single missing import crashes the **entire** custom node folder, preventing all your nodes from loading.

---

## Complete Working Example

```python
# nodes_optional_deps.py

import sys
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency imports with graceful degradation
# ---------------------------------------------------------------------------

_IMPORT_ERRORS = []

# scipy — used for spline interpolation
try:
    from scipy.interpolate import CubicSpline
    HAS_SCIPY = True
except ImportError as e:
    HAS_SCIPY = False
    _IMPORT_ERRORS.append(("scipy", str(e)))
    logger.warning("scipy not available. SplineInterpolationNode will be disabled. Install with: pip install scipy")

# open3d — used for point cloud processing
try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError as e:
    HAS_OPEN3D = False
    _IMPORT_ERRORS.append(("open3d", str(e)))
    logger.warning("open3d not available. PointCloudNode will be disabled. Install with: pip install open3d")

# trimesh — used for 3D mesh operations
try:
    import trimesh
    HAS_TRIMESH = True
except ImportError as e:
    HAS_TRIMESH = False
    _IMPORT_ERRORS.append(("trimesh", str(e)))
    logger.warning("trimesh not available. MeshProcessNode will be disabled. Install with: pip install trimesh")

# requests — usually available but handle gracefully
try:
    import requests
    HAS_REQUESTS = True
except ImportError as e:
    HAS_REQUESTS = False
    _IMPORT_ERRORS.append(("requests", str(e)))
    logger.warning("requests not available. APIFetchNode will be disabled.")

# xformers — GPU-specific, may not be installed
try:
    import xformers
    import xformers.ops
    HAS_XFORMERS = True
except ImportError as e:
    HAS_XFORMERS = False
    _IMPORT_ERRORS.append(("xformers", str(e)))
    logger.info("xformers not available. Memory-efficient attention will not be used.")

# Pillow — very common, but still handle it
try:
    from PIL import Image, ImageFilter, ImageEnhance
    HAS_PIL = True
except ImportError as e:
    HAS_PIL = False
    _IMPORT_ERRORS.append(("Pillow", str(e)))
    logger.warning("Pillow not available. Image processing nodes will be disabled.")


# ---------------------------------------------------------------------------
# Helper: require a dependency or raise a clear error
# ---------------------------------------------------------------------------

def require_package(package_name: str, has_flag: bool):
    """Raise a user-friendly error if a required package is missing."""
    if not has_flag:
        error_msg = f"Missing required package: {package_name}. Install with: pip install {package_name}"
        logger.error(error_msg)
        raise ImportError(error_msg)


# ---------------------------------------------------------------------------
# Nodes that use optional dependencies
# ---------------------------------------------------------------------------

class SplineInterpolationNode:
    """Interpolate between keyframe values using cubic splines."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "keyframes": ("STRING", {
                    "multiline": True,
                    "default": "0:0.0\n10:1.0\n20:0.5\n30:1.0",
                    "tooltip": "frame:value pairs, one per line"
                }),
                "num_frames": ("INT", {"default": 30, "min": 1, "max": 9999, "step": 1}),
                "loop": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("interpolated_values",)
    FUNCTION = "interpolate"
    CATEGORY = "animation"

    def interpolate(self, keyframes: str, num_frames: int, loop: bool):
        require_package("scipy", HAS_SCIPY)

        # Parse keyframes
        frames = []
        values = []
        for line in keyframes.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) == 2:
                frames.append(float(parts[0].strip()))
                values.append(float(parts[1].strip()))

        if len(frames) < 2:
            raise ValueError("At least 2 keyframes are required.")

        if loop and len(frames) >= 3:
            # Close the loop by appending the first point
            frames.append(frames[-1] + (frames[1] - frames[0]))
            values.append(values[0])

        # Create spline
        cs = CubicSpline(frames, values, bc_type="natural")

        # Evaluate at each frame
        result = []
        for i in range(num_frames):
            t = frames[0] + (frames[-1] - frames[0]) * (i / max(num_frames - 1, 1))
            val = float(cs(t))
            result.append(f"{i}:{val:.6f}")

        return ("\n".join(result),)


class PointCloudNode:
    """Process a 3D point cloud using open3d."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "point_data": ("STRING", {
                    "multiline": True,
                    "default": "0,0,0\n1,0,0\n0,1,0\n0,0,1",
                    "tooltip": "x,y,z per line"
                }),
                "voxel_size": ("FLOAT", {"default": 0.05, "min": 0.001, "max": 1.0, "step": 0.001}),
                "operation": (["downsample", "estimate_normals", "remove_outliers"],),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("processed_points",)
    FUNCTION = "process"
    CATEGORY = "3d"

    def process(self, point_data: str, voxel_size: float, operation: str):
        require_package("open3d", HAS_OPEN3D)

        # Parse points
        points = []
        for line in point_data.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) == 3:
                points.append([float(x) for x in parts])

        if not points:
            raise ValueError("No valid points provided.")

        # Create point cloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        # Process
        if operation == "downsample":
            pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
        elif operation == "estimate_normals":
            pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=voxel_size * 2, max_nn=30
            ))
        elif operation == "remove_outliers":
            pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

        # Serialize back to string
        result_points = [f"{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}" for p in pcd.points]
        return ("\n".join(result_points),)


class MeshProcessNode:
    """Process 3D meshes using trimesh."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vertices": ("STRING", {
                    "multiline": True,
                    "tooltip": "x,y,z per line"
                }),
                "faces": ("STRING", {
                    "multiline": True,
                    "tooltip": "i,j,k per line (face indices)"
                }),
                "operation": (["smooth", "subdivide", "simplify"],),
                "iterations": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("out_vertices", "out_faces",)
    FUNCTION = "process"
    CATEGORY = "3d"

    def process(self, vertices: str, faces: str, operation: str, iterations: int):
        require_package("trimesh", HAS_TRIMESH)

        # Parse vertices
        verts = []
        for line in vertices.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) == 3:
                verts.append([float(x) for x in parts])

        # Parse faces
        face_list = []
        for line in faces.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) == 3:
                face_list.append([int(x) for x in parts])

        mesh = trimesh.Trimesh(vertices=verts, faces=face_list)

        if operation == "smooth":
            for _ in range(iterations):
                mesh = trimesh.smoothing.filter_laplacian(mesh)
        elif operation == "subdivide":
            for _ in range(iterations):
                mesh = mesh.subdivide()
        elif operation == "simplify":
            target = max(len(mesh.faces) // (2 ** iterations), 4)
            mesh = mesh.simplify_quadric_decimation(target)

        out_verts = "\n".join(f"{v[0]:.6f},{v[1]:.6f},{v[2]:.6f}" for v in mesh.vertices)
        out_faces = "\n".join(f"{f[0]},{f[1]},{f[2]}" for f in mesh.faces)

        return (out_verts, out_faces)


class MemoryEfficientAttentionNode:
    """Uses xformers for memory-efficient attention if available, falls back to standard."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "use_xformers": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Use xformers if available"
                }),
                "query": ("TENSOR",),
                "key": ("TENSOR",),
                "value": ("TENSOR",),
            },
        }

    RETURN_TYPES = ("TENSOR",)
    FUNCTION = "attention"
    CATEGORY = "attention"

    def attention(self, use_xformers: bool, query, key, value):
        import torch
        import torch.nn.functional as F

        if use_xformers and HAS_XFORMERS:
            try:
                result = xformers.ops.memory_efficient_attention(query, key, value)
                return (result,)
            except Exception as e:
                logger.warning(f"xformers attention failed, falling back to standard: {e}")

        # Standard attention fallback
        scale = query.shape[-1] ** -0.5
        attn = torch.matmul(query, key.transpose(-2, -1)) * scale
        attn = torch.softmax(attn, dim=-1)
        result = torch.matmul(attn, value)
        return (result,)


class ImportStatusNode:
    """Reports which optional dependencies are available."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status_report",)
    FUNCTION = "report"
    CATEGORY = "debug"

    def report(self):
        lines = ["=== Dependency Status ==="]
        lines.append("")

        if _IMPORT_ERRORS:
            lines.append("MISSING PACKAGES:")
            for pkg, err in _IMPORT_ERRORS:
                lines.append(f"  - {pkg}: {err}")
            lines.append("")

        lines.append("AVAILABLE:")
        available = {
            "scipy": HAS_SCIPY,
            "open3d": HAS_OPEN3D,
            "trimesh": HAS_TRIMESH,
            "requests": HAS_REQUESTS,
            "xformers": HAS_XFORMERS,
            "Pillow": HAS_PIL,
        }
        for pkg, available_flag in available.items():
            status = "OK" if available_flag else "MISSING"
            lines.append(f"  - {pkg}: {status}")

        return ("\n".join(lines),)


# ---------------------------------------------------------------------------
# Conditional NODE_CLASS_MAPPINGS
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Only register nodes whose dependencies are available
if HAS_SCIPY:
    NODE_CLASS_MAPPINGS["SplineInterpolationNode"] = SplineInterpolationNode
    NODE_DISPLAY_NAME_MAPPINGS["SplineInterpolationNode"] = "Spline Interpolation"

if HAS_OPEN3D:
    NODE_CLASS_MAPPINGS["PointCloudNode"] = PointCloudNode
    NODE_DISPLAY_NAME_MAPPINGS["PointCloudNode"] = "Point Cloud Processor"

if HAS_TRIMESH:
    NODE_CLASS_MAPPINGS["MeshProcessNode"] = MeshProcessNode
    NODE_DISPLAY_NAME_MAPPINGS["MeshProcessNode"] = "Mesh Processor"

# Always register (uses fallbacks)
NODE_CLASS_MAPPINGS["MemoryEfficientAttentionNode"] = MemoryEfficientAttentionNode
NODE_DISPLAY_NAME_MAPPINGS["MemoryEfficientAttentionNode"] = "Memory-Efficient Attention"

NODE_CLASS_MAPPINGS["ImportStatusNode"] = ImportStatusNode
NODE_DISPLAY_NAME_MAPPINGS["ImportStatusNode"] = "Import Status"
```

---

## Pattern Structure

```
try:
    import optional_package
    HAS_PACKAGE = True
except ImportError as e:
    HAS_PACKAGE = False
    _IMPORT_ERRORS.append(("package_name", str(e)))
    logger.warning("package_name not available. Nodes X, Y will be disabled.")
```

### Key elements:

1. **`try/except ImportError`** — catches missing packages without crashing
2. **`HAS_*` flag** — boolean checked at runtime in node code
3. **`_IMPORT_ERRORS` list** — accumulates all failures for reporting
4. **`logger.warning()`** — logs the issue so users can find it in the console
5. **Conditional `NODE_CLASS_MAPPINGS`** — only registers nodes whose deps are satisfied

---

## Key Considerations

| Concern | Guidance |
|---|---|
| **Scope** | Wrap **individual** imports, not the entire file. Other nodes should still load if one dependency is missing. |
| **`ImportError` vs `Exception`** | Catch `ImportError` for missing packages. Catch `Exception` only if you know a specific package can fail in unexpected ways during import (e.g., DLL errors on Windows). |
| **`_IMPORT_ERRORS`** | Keep a list so you can display it in a debug node or log it once at startup. Don't just `pass` silently. |
| **`logger.warning`** | Use `logging.warning()` so the message appears in ComfyUI's console. Don't use `print()` — it may be suppressed. |
| **`require_package()`** | Use a helper function to raise clear errors at **execution time**, not import time. This lets nodes register even if their dep is missing (they just fail when used). |
| **Conditional mapping** | Two strategies: (A) Always register nodes and fail at execution with a clear error, or (B) Conditionally register only when deps are available. Use (B) for heavy deps that users are unlikely to install. |
| **Version pinning** | If a package has API changes across versions, check the version after import: `if HAS_PACKAGE and version.parse(package.__version__) < version.parse("1.5.0"): ...` |
| **Circular imports** | Some packages import heavy submodules at import time. If import is slow, consider lazy imports inside the `FUNCTION` method instead. |

---

## Variations

### 1. Lazy Import (Import at Execution Time)

```python
class HeavyNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",)}}

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "image"

    def process(self, image):
        # Import only when the node is actually used
        try:
            from heavy_library import process_image
        except ImportError:
            raise ImportError("heavy_library is required. pip install heavy-library")

        return (process_image(image),)
```

### 2. Fallback Implementation

```python
try:
    from scipy.ndimage import gaussian_filter
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

def apply_gaussian_blur(image, sigma):
    if HAS_SCIPY:
        return gaussian_filter(image, sigma=sigma)
    else:
        # Pure numpy fallback (slower)
        from numpy import convolve
        # ... manual implementation ...
        return blurred_image
```

### 3. Optional Accelerator

```python
try:
    import triton
    HAS_TRITON = True
except ImportError:
    HAS_TRITON = False

class OptimizedNode:
    def process(self, tensor):
        if HAS_TRITON:
            return self._triton_process(tensor)
        else:
            return self._torch_process(tensor)

    def _triton_process(self, tensor):
        # Triton kernel
        ...

    def _torch_process(self, tensor):
        # Standard PyTorch fallback
        ...
```

### 4. Platform-Specific Import

```python
import platform

HAS_CUDA = False
try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    pass

HAS_MPS = False
if platform.system() == "Darwin":
    try:
        import torch
        HAS_MPS = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    except ImportError:
        pass
```

### 5. Version-Conditional Import

```python
try:
    import diffusers
    from packaging import version
    HAS_DIFFUSERS = True
    DIFFUSERS_VERSION = version.parse(diffusers.__version__)
except ImportError:
    HAS_DIFFUSERS = False
    DIFFUSERS_VERSION = None

class DiffusersNode:
    def process(self, ...):
        require_package("diffusers", HAS_DIFFUSERS)

        if DIFFUSERS_VERSION >= version.parse("0.21.0"):
            # New API
            from diffusers import StableDiffusionXLPipeline as Pipeline
        else:
            # Old API
            from diffusers import StableDiffusionPipeline as Pipeline
```
