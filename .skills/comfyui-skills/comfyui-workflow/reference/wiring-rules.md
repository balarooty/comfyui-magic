# ComfyUI Wiring Rules

Rules for connecting nodes together in ComfyUI workflows.

---

## Data Flow Direction

Data flows from **output** to **input**:

```
[Source Node].outputs[slot_index]  →  [Dest Node].inputs[slot_index]
```

A link always goes from one node's output socket to another node's input socket. Connections are never bidirectional.

---

## Link Creation Format

A link is a 6-element array:

```json
[link_id, source_node_id, source_output_slot, dest_node_id, dest_input_slot, type_string]
```

To create a new connection:
1. Choose a source node and one of its output slots
2. Choose a destination node and one of its input slots
3. Verify type compatibility (see below)
4. Generate a unique `link_id` (increment `last_link_id`)
5. Add the link array to the `links` array
6. Update the source output's `links` array to include the new link_id
7. Set the destination input's `link` field to the new link_id

### Adding a Link

```python
# Generate new link ID
link_id = workflow["last_link_id"] + 1
workflow["last_link_id"] = link_id

# Create the link
link = [link_id, source_node_id, source_output_slot, dest_node_id, dest_input_slot, type_string]
workflow["links"].append(link)

# Update source output
source_node["outputs"][source_output_slot]["links"].append(link_id)

# Update destination input
dest_node["inputs"][dest_input_slot]["link"] = link_id
```

### Removing a Link

```python
# Find and remove from links array
workflow["links"] = [l for l in workflow["links"] if l[0] != link_id]

# Remove from source output's links array
source_node["outputs"][source_output_slot]["links"].remove(link_id)

# Clear destination input
dest_node["inputs"][dest_input_slot]["link"] = None
```

---

## Type Matching Rules

### Exact Type Match Required

An output can only connect to an input of the **same type**. Type matching is case-sensitive and exact.

- `MODEL` → `MODEL` ✓
- `MODEL` → `CLIP` ✗
- `MODEL` → `model` ✗

### Type Compatibility Matrix

| Output Type | Connects To |
|---|---|
| MODEL | MODEL |
| CLIP | CLIP |
| VAE | VAE |
| CONDITIONING | CONDITIONING |
| LATENT | LATENT |
| IMAGE | IMAGE |
| MASK | MASK |
| SAMPLER | SAMPLER |
| SIGMAS | SIGMAS |
| NOISE | NOISE |
| GUIDER | GUIDER |
| CONTROL_NET | CONTROL_NET |
| IPADAPTER_MODEL | IPADAPTER_MODEL |
| CLIP_VISION | CLIP_VISION |
| STYLE_MODEL | STYLE_MODEL |
| INT | INT |
| FLOAT | FLOAT |
| STRING | STRING |
| BOOLEAN | BOOLEAN |
| * (wildcard) | Any type |
| Any type | * (wildcard) |

### Wildcard Type

Some nodes use the wildcard type `*` which accepts connections from any type. This is used by utility nodes, reroute nodes, and generic pass-through nodes.

- An output of type `*` can connect to any input
- Any output can connect to an input of type `*`

---

## Input Connection Rules

### Single Connection Per Input

Each input socket can have **at most one** incoming connection. If you connect a new link to an input that already has a connection, the old link is replaced.

```
Node A (output) → Node C (input 0)  ✓
Node B (output) → Node C (input 0)  ✗ (replaces connection from A)
```

### Unconnected Inputs

If an input is not connected, it uses its widget value (if it has a widget) or the node's default behavior. Some inputs are required and must be connected.

### forceInput Inputs

Some inputs are marked as `forceInput: true` in the node definition. These inputs:
- Always display as a socket (never show a widget)
- Must be connected to function properly
- Cannot have inline widget values

Example: The `clip` input on `CLIPTextEncode` is forceInput.

---

## Output Connection Rules

### Multiple Connections Allowed

A single output socket can connect to **multiple** input sockets. The output data is shared (not copied) with all connected inputs.

```
Node A (output 0) → Node B (input 0)  ✓
Node A (output 0) → Node C (input 0)  ✓
Node A (output 0) → Node D (input 0)  ✓
```

### Tracking Multiple Connections

The output's `links` array contains all link IDs:

```json
{
  "name": "MODEL",
  "type": "MODEL",
  "links": [1, 5, 8],
  "slot_index": 0
}
```

This output is connected to three different inputs via links 1, 5, and 8.

---

## Slot Index Mapping

### Input Slots

Input slots are indexed by their position in the node's `inputs` array:

```
"inputs": [
  {"name": "model",    "type": "MODEL",         "link": 1,    "slot_index": 0},
  {"name": "positive", "type": "CONDITIONING",  "link": 3,    "slot_index": 1},
  {"name": "negative", "type": "CONDITIONING",  "link": null, "slot_index": 2},
  {"name": "latent_image", "type": "LATENT",    "link": 4,    "slot_index": 3}
]
```

- Input `model` is at slot 0
- Input `positive` is at slot 1
- Input `negative` is at slot 2
- Input `latent_image` is at slot 3

### Output Slots

Output slots are indexed by their position in the node's `outputs` array:

```
"outputs": [
  {"name": "MODEL",  "type": "MODEL",  "links": [1],    "slot_index": 0},
  {"name": "CLIP",   "type": "CLIP",   "links": [2],    "slot_index": 1},
  {"name": "VAE",    "type": "VAE",    "links": [],     "slot_index": 2}
]
```

- Output `MODEL` is at slot 0
- Output `CLIP` is at slot 1
- Output `VAE` is at slot 2

### Link References

When a link references slots, it uses these indices:

```json
[link_id, source_node_id, source_output_slot, dest_node_id, dest_input_slot, type]
```

For example: `[1, 4, 0, 3, 0, "MODEL"]`
- Source: Node 4, Output slot 0 (MODEL)
- Dest: Node 3, Input slot 0 (model)

---

## Widget Values and Links

### Widget Hidden When Linked

When an input has both a widget and a socket, connecting a link to the input **hides the widget** and the widget's value is not used. The linked data takes precedence.

```
Before linking:
  Input "steps" (INT) → widget showing "20"
  
After linking:
  Input "steps" (INT) → connected to output, widget hidden
```

### Widget Visible When Unlinked

When an input socket is not connected, the widget is visible and its value is used as the input data.

### Force Input (No Widget)

Inputs marked as `forceInput` never have widgets. They always show as sockets and require a connection.

### Widget Value Ordering Impact

When an input gets linked, its widget value is **removed** from the `widgets_values` array. This shifts the indices of subsequent widget values.

Before:
```json
"widgets_values": [123456, "randomize", 20, 7.5, "euler", "normal", 1.0]
```

After linking the `positive` conditioning input (which is between CLIP and the sampler):
```json
"widgets_values": [123456, "randomize", 20, 7.5, "euler", "normal", 1.0]
```

Note: The widget values for inputs that are connected via links are simply omitted from the array. The ordering is based on which widgets are visible.

---

## Lazy Evaluation Links

ComfyUI supports lazy evaluation. Some inputs are marked as lazy, meaning the connected node is only evaluated when the data is actually needed.

### Lazy Input Behavior

- Lazy inputs are evaluated on-demand, not eagerly
- This allows conditional execution paths
- Nodes that don't use a lazy input's data won't trigger evaluation of the source

### Identifying Lazy Inputs

Lazy inputs are defined in the node's `INPUT_TYPES` with `lazy=True`:

```python
@classmethod
def INPUT_TYPES(s):
    return {
        "required": {
            "image": ("IMAGE",),
        },
        "optional": {
            "mask": ("MASK", {"lazy": True}),
        }
    }
```

### Lazy Evaluation Pattern

```
If Node A has a lazy input that connects to Node B:
- Node B is only executed when Node A requests the data
- If Node A skips the lazy input (e.g., conditional), Node B is not executed
```

---

## Reroute Nodes

Reroute nodes are utility nodes that pass data through without modification. They are used for visual organization.

### Reroute Node Properties

- Input type: `*` (wildcard, accepts any type)
- Output type: `*` (wildcard, outputs same type as input)
- No processing; pure pass-through

### Using Reroute Nodes

```
Source Node (IMAGE) → Reroute (*) → Dest Node (IMAGE)
```

The reroute node automatically adapts its output type to match the connected input type.

---

## Error Conditions

### Type Mismatch

Connecting incompatible types produces an error or the link is displayed as invalid (red).

### Missing Required Input

Nodes with required inputs that are not connected will fail during execution.

### Circular Dependencies

ComfyUI detects circular dependencies and prevents execution. A node cannot (directly or indirectly) feed data back to itself.

### Orphaned Nodes

Nodes that are not connected to any output path (leading to SaveImage, PreviewImage, or other terminal nodes) are not executed.

---

## Best Practices

### Connection Hygiene

1. **Verify types before connecting**: Check that output type matches input type
2. **Use slot_index for references**: Always use `slot_index` for identifying input/output positions
3. **Clean up removed links**: When removing a link, update both the source output's `links` array and the destination input's `link` field

### Layout Conventions

1. **Left-to-right flow**: Place source nodes on the left, destination nodes on the right
2. **Group related nodes**: Use group boxes to visually organize pipeline stages
3. **Minimize link crossings**: Arrange nodes to reduce overlapping links

### Link Management

1. **One output → many inputs**: A single output can feed multiple downstream nodes
2. **One input → one output**: Each input accepts only one connection
3. **Use Reroute for clarity**: Add reroute nodes to simplify complex wiring
4. **Document with groups**: Use group titles to describe pipeline stages
