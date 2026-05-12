# Node Expansion via `expand` Dict

## When to Use

- You want a single node to dynamically create an entire subgraph at execution time.
- You need loops, conditional branching, or dynamic fan-out that the static node graph can't express.
- You want a "macro" node that expands into multiple primitive nodes based on runtime inputs.

## Problem

ComfyUI's graph is static — nodes and connections are fixed when the user clicks Queue. You can't create new nodes or wire them at runtime from Python.

## Solution: Return `{"expand": graph_dict}` from `execute()`

When a node's `execute()` returns a dict with an `"expand"` key containing a graph definition, ComfyUI creates that subgraph and substitutes it for the node's outputs.

```python
class DynamicPromptChain:
    """
    Takes N prompt segments and expands into a chain of
    CLIPTextEncode → Combine node, one per segment.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "segments": ("STRING", {
                    "multiline": True,
                    "default": "a cat\nin a garden\npainted by monet",
                    "tooltip": "One prompt per line"
                }),
                "separator": ("STRING", {"default": ", "}),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "execute"
    CATEGORY = "conditioning"

    def execute(self, clip, segments, separator):
        lines = [s.strip() for s in segments.strip().split("\n") if s.strip()]

        if not lines:
            raise ValueError("No prompt segments provided")

        if len(lines) == 1:
            # No expansion needed — single prompt
            from nodes import CLIPTextEncode
            node = CLIPTextEncode()
            return node.encode(clip, lines[0])

        # Build the expand graph
        nodes = {}
        node_order = []

        for i, line in enumerate(lines):
            # Each segment gets a CLIPTextEncode node
            nodes[f"encode_{i}"] = {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": line,
                    "clip": ["__input__", "clip"],  # reference to our input
                },
            }
            node_order.append(f"encode_{i}")

        # Combine conditionings sequentially
        # First conditioning comes directly from encode_0
        # Each subsequent one merges via ConditioningCombine
        prev = f"encode_0"
        for i in range(1, len(lines)):
            combine_name = f"combine_{i}"
            nodes[combine_name] = {
                "class_type": "ConditioningCombine",
                "inputs": {
                    "conditioning_1": [prev, 0],  # output index 0 of prev
                    "conditioning_2": [f"encode_{i}", 0],
                },
            }
            node_order.append(combine_name)
            prev = combine_name

        # The last node's output is our output
        last_node = prev

        return {
            "expand": {
                "nodes": nodes,
                "output": [last_node, 0],  # [node_name, output_index]
            }
        }


class ConditionalUpscale:
    """
    Conditionally expand into an upscale path or pass-through
    based on image resolution.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "upscale_model": ("UPSCALE_MODEL",),
                "target_width": ("INT", {"default": 1024, "min": 64, "max": 8192}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"
    CATEGORY = "image/upscaling"

    def execute(self, image, upscale_model, target_width):
        _, h, w, _ = image.shape

        if w >= target_width:
            # Already large enough — return identity (no-op expand)
            return {
                "expand": {
                    "nodes": {},
                    "output": ["__input__", "image"],  # pass through
                }
            }

        # Expand into upscale path
        return {
            "expand": {
                "nodes": {
                    "upscale": {
                        "class_type": "ImageUpscaleWithModel",
                        "inputs": {
                            "upscale_model": ["__input__", "upscale_model"],
                            "image": ["__input__", "image"],
                        },
                    },
                    "scale_down": {
                        "class_type": "ImageScale",
                        "inputs": {
                            "image": ["upscale", 0],
                            "width": target_width,
                            "height": 0,  # auto
                            "upscale_method": "lanczos",
                            "crop": "disabled",
                        },
                    },
                },
                "output": ["scale_down", 0],
            }
        }


class BatchProcess:
    """
    Expand into N copies of a processing chain, one per image in the batch.
    Demonstrates dynamic fan-out.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True}),
                "clip": ("CLIP",),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "execute"
    CATEGORY = "conditioning"

    def execute(self, images, prompt, clip):
        batch_size = images.shape[0]

        nodes = {}
        prev_cond = None

        for i in range(batch_size):
            # Unique text per image in batch
            text = f"{prompt} [variation {i}]"

            nodes[f"encode_{i}"] = {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": text,
                    "clip": ["__input__", "clip"],
                },
            }

            if prev_cond is None:
                prev_cond = f"encode_{i}"
            else:
                combine = f"combine_{i}"
                nodes[combine] = {
                    "class_type": "ConditioningCombine",
                    "inputs": {
                        "conditioning_1": [prev_cond, 0],
                        "conditioning_2": [f"encode_{i}", 0],
                    },
                }
                prev_cond = combine

        return {
            "expand": {
                "nodes": nodes,
                "output": [prev_cond, 0] if prev_cond else ["__input__", "clip"],
            }
        }


NODE_CLASS_MAPPINGS = {
    "DynamicPromptChain": DynamicPromptChain,
    "ConditionalUpscale": ConditionalUpscale,
    "BatchProcess": BatchProcess,
}
```

## Graph Dict Format

```python
{
    "expand": {
        "nodes": {
            "node_name": {
                "class_type": "ComfyNodeType",   # must be a registered node
                "inputs": {
                    "param": "literal_value",      # string, int, float, bool
                    "param": ["other_node", 0],    # link: [source_name, output_index]
                    "param": ["__input__", "name"], # reference this node's input
                },
            },
            # ... more nodes
        },
        "output": ["node_name", output_index],  # which node feeds our RETURN_TYPES
    }
}
```

| Key | Meaning |
|---|---|
| `"__input__"` | References an input of the expanding node itself |
| `["node_name", N]` | References output N of another node in the expand graph |
| `"literal_value"` | A string/number/bool passed directly |

## Key Considerations

1. **Class types must exist** — Every `class_type` must be a registered ComfyUI node. Use built-in nodes or other custom nodes.
2. **`"output"` is required** — You must specify which node and output index maps to your node's `RETURN_TYPES`. Without it, ComfyUI doesn't know what to pass downstream.
3. **No circular references** — The expand graph is a DAG. Circular dependencies will deadlock the executor.
4. **Input references** — `["__input__", "name"]` lets the expanded graph read from the parent node's inputs. The `"name"` must match a key in your `INPUT_TYPES`.
5. **Execution order** — ComfyUI's executor resolves dependencies automatically. You don't need to topologically sort the nodes.
6. **Error handling** — If the expand dict is malformed, ComfyUI will raise an error during graph resolution. Validate your structure before returning.
7. **Performance** — Each expansion creates real nodes in the execution graph. Large expansions (hundreds of nodes) may slow graph resolution. Consider batching or loop nodes for heavy workloads.
8. **Nested expansion** — Expanded nodes can themselves expand. Use carefully — deep nesting makes debugging difficult.
9. **Pass-through** — Return `{"expand": {"nodes": {}, "output": ["__input__", "input_name"]}}` to create a no-op identity node.
