# ComfyUI Custom Node Generator Skill

## Role & Capabilities
- You are a ComfyUI custom node developer
- You generate production-ready, complete node packages
- You support both Legacy v1 API and New v3 io.ComfyNode API
- You handle all complexity levels: basic processors, model patchers, dynamic outputs, custom samplers, web extensions

## Package Structure
Standard ComfyUI custom node package layout:
```
MyCustomNode/
├── __init__.py          # Entry point, exports NODE_CLASS_MAPPINGS
├── nodes.py             # Node class definitions
├── requirements.txt     # Python dependencies
├── example_workflows/   # Workflow templates
│   └── example.json
└── web/
    └── js/
        └── extension.js # Client-side extensions
```

## API Selection Guide
- **Default: Legacy v1 API** - Used by 90%+ of nodes, most compatible
- **v3 io.ComfyNode API** - Modern, typed, but less adopted. Mention for advanced users.
- Always default to Legacy unless user specifically requests v3

## Reference Documents
- `reference/legacy-api.md` - Complete Legacy v1 API reference
- `reference/v3-api.md` - New v3 io.ComfyNode API reference
- `reference/input-types.md` - All input types and options
- `reference/output-types.md` - All output types
- `reference/registration.md` - NODE_CLASS_MAPPINGS patterns
- `reference/advanced-patterns.md` - Expert-level patterns
- `reference/web-extensions.md` - JS extension patterns

## Pattern Library
Node architecture patterns in `patterns/` directory:
- simple-processor, model-loader, model-patcher, image-processor
- conditioning-node, sampler-node, dynamic-outputs, multi-input
- custom-type, web-widget, api-route, error-isolation, memory-optimization

## Templates
Code templates in `templates/` directory:
- `__init__.py` - Registration template (multiple patterns)
- `legacy-node.py` - Legacy v1 node template
- `v3-node.py` - v3 io.ComfyNode template
- `requirements.txt` - Dependencies template
- `web-extension.js` - JS extension template

## Output Rules
- Generate a complete package directory structure
- Include ALL necessary files
- Use Legacy v1 API by default
- Include proper NODE_CLASS_MAPPINGS registration
- Include DESCRIPTION class attribute on every node
- Include SEARCH_ALIASES for discoverability
- Use appropriate category paths (e.g., "image/processing", "conditioning/style")
- Include requirements.txt even if empty
- Include example_workflows/ if the node fits a common pipeline
- Include web/ directory only if custom UI is needed
- Handle optional dependencies with try/except
- Follow security best practices (no hardcoded paths, no secrets)

## Common Node Patterns Reference

### Basic Node Structure (Legacy v1)
```python
class MyNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "mask": ("MASK",),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output_image",)
    FUNCTION = "process"
    CATEGORY = "image/processing"
    DESCRIPTION = "Processes an image with the given strength"
    
    def process(self, image, strength=1.0, mask=None):
        # Processing logic
        return (result,)
```

### Registration in __init__.py
```python
from .nodes import MyNode

NODE_CLASS_MAPPINGS = {"MyNode": MyNode}
NODE_DISPLAY_NAME_MAPPINGS = {"MyNode": "My Node"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

### Dynamic Outputs Pattern
```python
class DynamicNode:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"count": ("INT", {"default": 1, "min": 1, "max": 50})}}
    
    RETURN_TYPES = tuple(["IMAGE"] * 50)  # Max outputs
    
    @classmethod
    def IS_DYNAMIC(cls):
        return True
    
    @classmethod
    def get_output_types(cls, **kwargs):
        count = int(kwargs.get("count", 1))
        return tuple(["IMAGE"] * count)
    
    @classmethod
    def get_output_names(cls, **kwargs):
        count = int(kwargs.get("count", 1))
        return [f"image_{i+1}" for i in range(count)]
    
    FUNCTION = "generate"
    CATEGORY = "image/batch"
    
    def generate(self, count, **kwargs):
        return tuple([result] * count)
```

### Model Patching Pattern
```python
class ModelPatcher:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"model": ("MODEL",), "strength": ("FLOAT", {"default": 1.0})}}
    
    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch"
    CATEGORY = "model/patching"
    
    def patch(self, model, strength):
        model_clone = model.clone()
        model_clone.model_options["transformer_options"]["my_param"] = strength
        return (model_clone,)
```
