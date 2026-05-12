# Node Registration Reference

How to register custom nodes with ComfyUI via `NODE_CLASS_MAPPINGS` and related patterns.

## NODE_CLASS_MAPPINGS

The primary registration mechanism. A dict mapping internal class names to node classes.

### Simple Mapping

```python
from .nodes import MyNode, AnotherNode

NODE_CLASS_MAPPINGS = {
    "MyNode": MyNode,
    "AnotherNode": AnotherNode,
}
```

### Display Name Mapping

Optional `NODE_DISPLAY_NAME_MAPPINGS` dict for human-readable names in the UI.

```python
NODE_CLASS_MAPPINGS = {
    "MyNode": MyNode,
    "AnotherNode": AnotherNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MyNode": "My Custom Node",
    "AnotherNode": "Another Node",
}
```

### Display Name as String in Mapping

Some nodes use a tuple or string for the display name directly in the class mapping.

```python
NODE_CLASS_MAPPINGS = {
    "MyNode": MyNode,
    "MyNode_DisplayName": "My Custom Node",
}
```

## NODE_CONFIG Pattern (KJNodes Style)

Define node configurations in a dict, then generate class mappings.

```python
NODE_CONFIG = {
    "MyNode": {
        "class": MyNode,
        "display_name": "My Node",
        "description": "Does something useful",
    },
    "AnotherNode": {
        "class": AnotherNode,
        "display_name": "Another Node",
        "description": "Does something else",
    },
}

NODE_CLASS_MAPPINGS = {k: v["class"] for k, v in NODE_CONFIG.items()}
NODE_DISPLAY_NAME_MAPPINGS = {k: v["display_name"] for k, v in NODE_CONFIG.items()}
```

## generate_node_mappings Helper

Reusable function to generate mappings from a list of node classes.

```python
def generate_node_mappings(*node_classes):
    """Generate NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS from node classes."""
    class_mappings = {}
    display_mappings = {}

    for cls in node_classes:
        name = cls.__name__
        display_name = getattr(cls, "DISPLAY_NAME", name)
        class_mappings[name] = cls
        display_mappings[name] = display_name

    return class_mappings, display_mappings


# Usage
NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = generate_node_mappings(
    ImageBlend,
    ImageBlur,
    ImageSharpen,
)
```

## WEB_DIRECTORY Export

Export the path to JavaScript extensions.

```python
WEB_DIRECTORY = "./web/js"
```

## __all__ Export List

Explicitly export the required variables.

```python
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
```

## Multiple Module Merge Pattern

Combine node mappings from multiple modules.

```python
from .image_nodes import NODE_CLASS_MAPPINGS as IMAGE_MAPPINGS
from .model_nodes import NODE_CLASS_MAPPINGS as MODEL_MAPPINGS
from .utility_nodes import NODE_CLASS_MAPPINGS as UTILITY_MAPPINGS

NODE_CLASS_MAPPINGS = {}
NODE_CLASS_MAPPINGS.update(IMAGE_MAPPINGS)
NODE_CLASS_MAPPINGS.update(MODEL_MAPPINGS)
NODE_CLASS_MAPPINGS.update(UTILITY_MAPPINGS)

NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS.update(IMAGE_DISPLAY_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(MODEL_DISPLAY_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(UTILITY_DISPLAY_MAPPINGS)
```

## Try/Except Import Isolation

Isolate optional dependencies to prevent import errors from breaking the entire package.

```python
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Core nodes (always available)
from .core_nodes import NODE_CLASS_MAPPINGS as CORE_MAPPINGS
NODE_CLASS_MAPPINGS.update(CORE_MAPPINGS)

# Optional: requires torch
try:
    from .torch_nodes import NODE_CLASS_MAPPINGS as TORCH_MAPPINGS
    NODE_CLASS_MAPPINGS.update(TORCH_MAPPINGS)
except ImportError:
    pass

# Optional: requires opencv
try:
    from .cv_nodes import NODE_CLASS_MAPPINGS as CV_MAPPINGS
    NODE_CLASS_MAPPINGS.update(CV_MAPPINGS)
except ImportError:
    pass

# Optional: requires specific GPU features
try:
    from .gpu_nodes import NODE_CLASS_MAPPINGS as GPU_MAPPINGS
    NODE_CLASS_MAPPINGS.update(GPU_MAPPINGS)
except (ImportError, RuntimeError):
    pass
```

## Empty Mappings

For infrastructure packages that don't provide nodes directly.

```python
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
```

## Complete __init__.py Template

```python
"""
My Custom Node Pack
Provides image processing and model manipulation nodes.
"""

from .image_nodes import ImageBlend, ImageBlur, ImageSharpen
from .model_nodes import ModelPatcher, ModelMerger
from .utility_nodes import MathNode, StringNode

NODE_CLASS_MAPPINGS = {
    "ImageBlend": ImageBlend,
    "ImageBlur": ImageBlur,
    "ImageSharpen": ImageSharpen,
    "ModelPatcher": ModelPatcher,
    "ModelMerger": ModelMerger,
    "MathNode": MathNode,
    "StringNode": StringNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageBlend": "Image Blend",
    "ImageBlur": "Image Blur",
    "ImageSharpen": "Image Sharpen",
    "ModelPatcher": "Model Patcher",
    "ModelMerger": "Model Merger",
    "MathNode": "Math",
    "StringNode": "String",
}

WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
```

## Modular __init__.py with Try/Except

```python
"""
My Node Pack with optional dependencies.
"""

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Core nodes
from .core import MathNode, StringNode, BooleanNode
NODE_CLASS_MAPPINGS.update({
    "MathNode": MathNode,
    "StringNode": StringNode,
    "BooleanNode": BooleanNode,
})

# Image nodes (always available with torch)
try:
    from .image import ImageBlend, ImageBlur
    NODE_CLASS_MAPPINGS.update({
        "ImageBlend": ImageBlend,
        "ImageBlur": ImageBlur,
    })
except ImportError:
    pass

# OpenCV nodes (optional)
try:
    from .cv_nodes import CVEdgeDetect, CVThreshold
    NODE_CLASS_MAPPINGS.update({
        "CVEdgeDetect": CVEdgeDetect,
        "CVThreshold": CVThreshold,
    })
except ImportError:
    pass

# Display names
NODE_DISPLAY_NAME_MAPPINGS = {
    "MathNode": "Math",
    "StringNode": "String",
    "BooleanNode": "Boolean",
    "ImageBlend": "Image Blend",
    "ImageBlur": "Image Blur",
    "CVEdgeDetect": "CV Edge Detect",
    "CVThreshold": "CV Threshold",
}

WEB_DIRECTORY = "./web/js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
```

## ComfyRegistry and pyproject.toml

For publishing to the ComfyUI registry, use `pyproject.toml` with a `[tool.comfy]` section.

```toml
[project]
name = "comfyui-my-node-pack"
version = "1.0.0"
description = "Custom nodes for image processing and model manipulation"
requires-python = ">=3.10"
dependencies = []

[project.urls]
Repository = "https://github.com/user/comfyui-my-node-pack"

[tool.comfy]
PublisherId = "your_publisher_id"
DisplayName = "My Node Pack"
Icon = "https://example.com/icon.png"
```

### pyproject.toml Fields

| Field                    | Description                                      |
|--------------------------|--------------------------------------------------|
| `name`                   | Package name (must be unique in registry)        |
| `version`                | Semantic version string                          |
| `description`            | Short package description                        |
| `PublisherId`            | Your ComfyUI registry publisher ID               |
| `DisplayName`            | Human-readable package name                      |
| `Icon`                   | URL to package icon                              |

## __init__.py with Version Info

```python
"""My Custom Node Pack - v1.2.0"""

__version__ = "1.2.0"

from .nodes import MyNode, AnotherNode

NODE_CLASS_MAPPINGS = {
    "MyNode": MyNode,
    "AnotherNode": AnotherNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MyNode": "My Node",
    "AnotherNode": "Another Node",
}

WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

print(f"[My Node Pack] Loaded {len(NODE_CLASS_MAPPINGS)} nodes")
```
