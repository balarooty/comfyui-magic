# Custom Data Type Definition Pattern

## When to Use

Use this pattern when your node produces or consumes data that does **not** fit any built-in ComfyUI type (`IMAGE`, `MODEL`, `CONDITIONING`, `LATENT`, etc.). Common cases:

- A list of prompts (e.g., for batch text processing)
- A structured configuration object
- A region-of-interest bounding box
- A custom embedding or feature vector

ComfyUI types are **plain strings**. You invent a new type string, use it in `RETURN_TYPES` / `INPUT_TYPES`, and optionally mark inputs as `forceInput=True` so they only accept connections (no widget).

---

## Complete Working Example: PROMPT_LIST

```python
# nodes_prompt_list.py

from typing import List, Tuple


class PromptListBuilder:
    """Builds a PROMPT_LIST from individual prompt strings."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts": ("STRING", {
                    "multiline": True,
                    "default": "a cat\na dog\na bird",
                    "tooltip": "One prompt per line"
                }),
                "separator": ("STRING", {
                    "default": "\n",
                    "tooltip": "Character(s) separating prompts"
                }),
            },
        }

    # Custom type: PROMPT_LIST
    RETURN_TYPES = ("PROMPT_LIST",)
    RETURN_NAMES = ("prompt_list",)
    FUNCTION = "build"
    CATEGORY = "text"

    def build(self, prompts: str, separator: str) -> Tuple[List[str]]:
        items = [p.strip() for p in prompts.split(separator) if p.strip()]
        if not items:
            raise ValueError("Prompt list is empty after splitting.")
        return (items,)


class PromptListSelector:
    """Selects a single prompt from a PROMPT_LIST by index."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_list": ("PROMPT_LIST", {"forceInput": True}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "select"
    CATEGORY = "text"

    def select(self, prompt_list: List[str], index: int) -> Tuple[str]:
        if index >= len(prompt_list):
            raise IndexError(
                f"Index {index} out of range (list has {len(prompt_list)} items)."
            )
        return (prompt_list[index],)


class PromptListConcat:
    """Concatenates two PROMPT_LIST inputs into one."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list_a": ("PROMPT_LIST", {"forceInput": True}),
                "list_b": ("PROMPT_LIST", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("PROMPT_LIST",)
    RETURN_NAMES = ("prompt_list",)
    FUNCTION = "concat"
    CATEGORY = "text"

    def concat(self, list_a: List[str], list_b: List[str]) -> Tuple[List[str]]:
        return (list_a + list_b,)


class PromptListLength:
    """Returns the number of prompts in a PROMPT_LIST."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_list": ("PROMPT_LIST", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("length",)
    FUNCTION = "get_length"
    CATEGORY = "text"

    def get_length(self, prompt_list: List[str]) -> Tuple[int]:
        return (len(prompt_list),)


NODE_CLASS_MAPPINGS = {
    "PromptListBuilder": PromptListBuilder,
    "PromptListSelector": PromptListSelector,
    "PromptListConcat": PromptListConcat,
    "PromptListLength": PromptListLength,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptListBuilder": "Prompt List Builder",
    "PromptListSelector": "Prompt List Selector",
    "PromptListConcat": "Prompt List Concat",
    "PromptListLength": "Prompt List Length",
}
```

---

## How It Works

### Type String Convention

```python
RETURN_TYPES = ("PROMPT_LIST",)
```

ComfyUI matches output types to input types by **exact string comparison**. `"PROMPT_LIST"` on an output will only connect to `"PROMPT_LIST"` on an input. The string is arbitrary — it just needs to be consistent across all nodes that use it.

### `forceInput=True`

```python
"prompt_list": ("PROMPT_LIST", {"forceInput": True}),
```

This tells ComfyUI:
- **Do not** render a widget for this input.
- The value **must** come from a connected output node.
- The input socket is always visible on the node.

### Type Aliasing

If you want multiple type strings to be interchangeable, you can use a list:

```python
# Accepts either MY_TYPE or compatible subtypes
"input_data": (["MY_TYPE", "MY_TYPE_V2"],),
```

Or define a type that is a superset:

```python
# COMBO_STYLE accepts both STRING and STYLED_STRING connections
"style": (["STRING", "STYLED_STRING"],),
```

### Internal Data Format

The custom type can carry **any Python object** through the graph. In the example above, `PROMPT_LIST` is simply a `List[str]`. For more complex data:

```python
# A structured config object
class ConfigBundle:
    def __init__(self, params: dict, metadata: dict):
        self.params = params
        self.metadata = metadata

# Node returns it
RETURN_TYPES = ("CONFIG_BUNDLE",)
def generate(self, ...):
    bundle = ConfigBundle(params={"steps": 20}, metadata={"version": 1})
    return (bundle,)
```

---

## Key Considerations

| Concern | Guidance |
|---|---|
| **Naming** | Use `UPPER_SNAKE_CASE` for type names to distinguish them from built-ins. Avoid names that collide with existing types. |
| **Documentation** | There is no central type registry. Document your custom types in your node pack's README. |
| **Serialization** | Custom types are **not** serialized when saving workflows — only their connections are. If a node must survive a reload, its inputs must be reconstructable from widgets or upstream nodes. |
| **`forceInput` vs widget** | Use `forceInput=True` when the input should always come from another node. Omit it if you want a fallback widget (e.g., a text box). |
| **Type compatibility** | A type string is just a string. There is no inheritance system. If you want `PROMPT_LIST_V2` to accept `PROMPT_LIST`, list both in the input type: `(["PROMPT_LIST", "PROMPT_LIST_V2"],)`. |
| **Debugging** | If a connection is refused, check that the output type string **exactly** matches the input type string (case-sensitive). |

---

## Variations

### 1. Bounding Box Type

```python
RETURN_TYPES = ("BBOX",)

def detect(self, image):
    # Returns dict with x, y, w, h
    bbox = {"x": 100, "y": 50, "w": 200, "h": 300}
    return (bbox,)
```

### 2. Typed List with Validation

```python
class EmbeddingList:
    """A list of torch tensors with shape validation."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "embeddings": ("EMBEDDING_LIST", {"forceInput": True}),
                "expected_dim": ("INT", {"default": 768, "min": 1}),
            },
        }

    RETURN_TYPES = ("EMBEDDING_LIST",)
    FUNCTION = "validate"
    CATEGORY = "embedding"

    def validate(self, embeddings, expected_dim):
        for i, emb in enumerate(embeddings):
            if emb.shape[-1] != expected_dim:
                raise ValueError(
                    f"Embedding {i} has dim {emb.shape[-1]}, expected {expected_dim}"
                )
        return (embeddings,)
```

### 3. Union Type (Multiple Accepted Types)

```python
# Accept either IMAGE or LATENT
"input_data": (["IMAGE", "LATENT"],),

# In FUNCTION, check the actual type
def process(self, input_data):
    if isinstance(input_data, dict):
        # LATENT is a dict with key "samples"
        tensor = input_data["samples"]
    else:
        # IMAGE is a torch.Tensor
        tensor = input_data
```

### 4. Custom Type with Metadata

```python
RETURN_TYPES = ("STYLE_PRESET",)

def create_style(self, prompt, negative, cfg, steps):
    preset = {
        "prompt": prompt,
        "negative": negative,
        "cfg": cfg,
        "steps": steps,
    }
    return (preset,)
```

Downstream nodes unpack the dict and use individual fields.
