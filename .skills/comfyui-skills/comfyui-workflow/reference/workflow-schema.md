# ComfyUI Workflow JSON Schema Reference

## Top-Level Structure

A ComfyUI workflow is a JSON object with the following top-level fields:

```
{
  "last_node_id": <int>,
  "last_link_id": <int>,
  "last_group_id": <int>,
  "nodes": [<Node>, ...],
  "links": [<Link>, ...],
  "groups": [<Group>, ...],
  "config": {},
  "extra": <Extra>,
  "version": <float>
}
```

| Field | Type | Description |
|---|---|---|
| `last_node_id` | int | Highest node ID assigned. Incremented when adding new nodes. |
| `last_link_id` | int | Highest link ID assigned. Incremented when adding new links. |
| `last_group_id` | int | Highest group ID assigned. Incremented when adding new groups. |
| `nodes` | array | All nodes in the workflow. |
| `links` | array | All connections between nodes. |
| `groups` | array | Visual grouping boxes on the canvas. |
| `config` | object | Workflow-level configuration (typically empty `{}`). |
| `extra` | object | Metadata including `ds` (canvas state), `info` (workflow info). |
| `version` | float | Workflow format version. Current: `0.4`. |

---

## Extra Object

```
"extra": {
  "ds": {
    "scale": <float>,
    "offset": [<float>, <float>]
  },
  "info": {
    "name": <string>,
    "author": <string>,
    "description": <string>,
    "version": <string>,
    "created_at": <string>
  }
}
```

---

## Node Object

Each node in the `nodes` array:

```
{
  "id": <int>,
  "type": <string>,
  "pos": [<float>, <float>],
  "size": {"0": <float>, "1": <float>},
  "flags": {},
  "order": <int>,
  "mode": <int>,
  "inputs": [<Input>, ...],
  "outputs": [<Output>, ...],
  "properties": {},
  "widgets_values": [...],
  "color": <string>,
  "bgcolor": <string>
}
```

| Field | Type | Description |
|---|---|---|
| `id` | int | Unique node identifier within the workflow. |
| `type` | string | Node class name (e.g. `"KSampler"`, `"CLIPTextEncode"`). |
| `pos` | [x, y] | Position on the canvas in pixels. |
| `size` | {0: w, 1: h} | Dimensions of the node widget. `{0: 315, 1: 262}` means width=315, height=262. |
| `flags` | object | Node-level flags. Usually `{}`. Can contain `"collapsed": true`. |
| `order` | int | Execution order index (calculated by ComfyUI, not user-set). |
| `mode` | int | Execution mode. See **Mode Values** below. |
| `inputs` | array | Input slots (sockets). See **Input Object**. |
| `outputs` | array | Output slots (sockets). See **Output Object**. |
| `properties` | object | Node properties. See **Properties Object**. |
| `widgets_values` | array | Values for widget controls on the node. See **Widget Values**. |
| `color` | string | Node title bar color in hex (e.g. `"#223"`). |
| `bgcolor` | string | Node body background color in hex (e.g. `"#335"`). |

---

## Input Object

Represents an input socket on a node.

```
{
  "name": <string>,
  "type": <string>,
  "link": <int|null>,
  "slot_index": <int>
}
```

| Field | Type | Description |
|---|---|---|
| `name` | string | Input name (e.g. `"model"`, `"positive"`, `"image"`). |
| `type` | string | Data type (e.g. `"MODEL"`, `"CLIP"`, `"CONDITIONING"`). |
| `link` | int or null | Link ID of the connected link, or `null` if unconnected. |
| `slot_index` | int | Index of this input in the node's input array. |

---

## Output Object

Represents an output socket on a node.

```
{
  "name": <string>,
  "type": <string>,
  "links": [<int>, ...],
  "slot_index": <int>,
  "shape": <int>
}
```

| Field | Type | Description |
|---|---|---|
| `name` | string | Output name (e.g. `"MODEL"`, `"LATENT"`, `"IMAGE"`). |
| `type` | string | Data type (e.g. `"MODEL"`, `"LATENT"`, `"IMAGE"`). |
| `links` | array of int | Link IDs of all connections from this output. Empty `[]` if unconnected. |
| `slot_index` | int | Index of this output in the node's output array. |
| `shape` | int | Socket shape. `2` = circle (default), `3` = diamond (for some types). |

---

## Link Array

Each link is represented as a flat array (not an object):

```
[link_id, source_node_id, source_output_slot, dest_node_id, dest_input_slot, type_string]
```

| Index | Type | Description |
|---|---|---|
| 0 | int | Unique link identifier. |
| 1 | int | ID of the source node (where the link originates). |
| 2 | int | Output slot index on the source node. |
| 3 | int | ID of the destination node (where the link terminates). |
| 4 | int | Input slot index on the destination node. |
| 5 | string | Data type string (e.g. `"MODEL"`, `"CLIP"`, `"LATENT"`). |

Example:
```json
[1, 4, 0, 3, 0, "MODEL"]
```
This means: Link #1 connects output slot 0 of node 4 to input slot 0 of node 3, carrying type "MODEL".

---

## Group Object

Visual grouping boxes on the canvas.

```
{
  "id": <int>,
  "bounding": [<float>, <float>, <float>, <float>],
  "color": <string>,
  "font_size": <int>,
  "flags": {},
  "title": <string>
}
```

| Field | Type | Description |
|---|---|---|
| `id` | int | Unique group identifier. |
| `bounding` | [x, y, w, h] | Position and size of the group box. |
| `color` | string | Group color in hex (e.g. `"#A15"`). |
| `font_size` | int | Font size for the group title. Default: `24`. |
| `flags` | object | Group-level flags. Usually `{}`. |
| `title` | string | Display title of the group (e.g. `"Loaders"`, `"Sampling"`). |

---

## Properties Object

Node properties stored on each node:

```
{
  "Node name for S&R": <string>,
  "cnr_id": <string>,
  "ver": [<int>, <int>],
  "models": [<ModelInfo>, ...]
}
```

| Field | Type | Description |
|---|---|---|
| `Node name for S&R` | string | Search & Replace name for the node. Used for node identification. |
| `cnr_id` | string | ComfyUI Node Registry ID. Format: `"comfyui-nodes:author.node_name@version"`. |
| `ver` | [int, int] | Node version as `[major, minor]`. |
| `models` | array | Model references used by the node. Contains `{"name": <string>, "url": <string>}`. |

---

## Widget Values

The `widgets_values` array contains values for the node's widget controls. The ordering follows these rules:

### Ordering Rules

1. **Required inputs first**: Values for required input widgets appear first, in the order they are defined in the node's `INPUT_TYPES` method.
2. **Optional inputs second**: Values for optional input widgets follow, in the order defined in `INPUT_TYPES`.
3. **Seed/combo widgets**: Seed widgets typically include a seed value and a control_after_generate option (e.g. `[123456, "randomize"]`).
4. **Converted inputs**: If an input is connected via a link, its widget value is omitted from the array (the widget is hidden).

### Common Widget Value Patterns

| Widget Type | Example Value |
|---|---|
| INT | `123456` |
| FLOAT | `7.5` |
| STRING | `"a prompt"` |
| STRING (multiline) | `"line1\nline2"` |
| BOOLEAN | `true` |
| COMBO | `"euler"` |
| Seed | `[seed_value, "randomize"]` or `[seed_value, "fixed"]` or `[seed_value, "increment"]` |
| Model combo | `"v1-5-pruned-emaonly.safetensors"` |

### Example

For a `KSampler` node:
```json
"widgets_values": [
  123456,           // seed (INT widget)
  "randomize",      // control_after_generate
  20,               // steps (INT)
  7.5,              // cfg (FLOAT)
  "euler",          // sampler_name (COMBO)
  "normal",         // scheduler (COMBO)
  1.0               // denoise (FLOAT)
]
```

---

## Mode Values

| Value | Name | Description |
|---|---|---|
| 0 | Always | Node executes normally. |
| 2 | Never | Node is muted/skipped. Outputs default values. |
| 4 | Bypass | Node is bypassed. Inputs pass through to outputs directly. |

### Mode Behavior

- **Mode 0 (Always)**: Standard execution. The node processes inputs and produces outputs.
- **Mode 2 (Never)**: The node does not execute. Downstream nodes receive null/default values. The node appears dimmed.
- **Mode 4 (Bypass)**: The node acts as a pass-through. The first input is forwarded to the first output, second input to second output, etc. Useful for temporarily disabling a node without breaking the pipeline.

---

## Version Field

The `version` field indicates the workflow format version:

| Value | Description |
|---|---|
| `0.4` | Current workflow format (LiteGraph-based). Used by ComfyUI frontend. |
| `0.4.0` | Alternative representation of 0.4. |
| `4` | API format version (used in the API, not the UI workflow). |

The API format is different from the UI workflow format. The API format uses `class_type` instead of `type`, and `inputs` is an object (key-value pairs) instead of an array.

---

## Complete Example

```json
{
  "last_node_id": 6,
  "last_link_id": 4,
  "last_group_id": 1,
  "nodes": [
    {
      "id": 1,
      "type": "CheckpointLoaderSimple",
      "pos": [100, 100],
      "size": {"0": 315, "1": 98},
      "flags": {},
      "order": 0,
      "mode": 0,
      "inputs": [],
      "outputs": [
        {"name": "MODEL", "type": "MODEL", "links": [1], "slot_index": 0},
        {"name": "CLIP", "type": "CLIP", "links": [2], "slot_index": 1},
        {"name": "VAE", "type": "VAE", "links": [], "slot_index": 2}
      ],
      "properties": {"Node name for S&R": "CheckpointLoaderSimple"},
      "widgets_values": ["v1-5-pruned-emaonly.safetensors"],
      "color": "",
      "bgcolor": ""
    },
    {
      "id": 2,
      "type": "CLIPTextEncode",
      "pos": [100, 250],
      "size": {"0": 400, "1": 200},
      "flags": {},
      "order": 1,
      "mode": 0,
      "inputs": [
        {"name": "clip", "type": "CLIP", "link": 2, "slot_index": 0}
      ],
      "outputs": [
        {"name": "CONDITIONING", "type": "CONDITIONING", "links": [3], "slot_index": 0}
      ],
      "properties": {"Node name for S&R": "CLIPTextEncode"},
      "widgets_values": ["a beautiful landscape"],
      "color": "",
      "bgcolor": ""
    },
    {
      "id": 3,
      "type": "EmptyLatentImage",
      "pos": [100, 500],
      "size": {"0": 315, "1": 106},
      "flags": {},
      "order": 2,
      "mode": 0,
      "inputs": [],
      "outputs": [
        {"name": "LATENT", "type": "LATENT", "links": [4], "slot_index": 0}
      ],
      "properties": {"Node name for S&R": "EmptyLatentImage"},
      "widgets_values": [512, 512, 1],
      "color": "",
      "bgcolor": ""
    },
    {
      "id": 4,
      "type": "KSampler",
      "pos": [500, 100],
      "size": {"0": 315, "1": 262},
      "flags": {},
      "order": 3,
      "mode": 0,
      "inputs": [
        {"name": "model", "type": "MODEL", "link": 1, "slot_index": 0},
        {"name": "positive", "type": "CONDITIONING", "link": 3, "slot_index": 1},
        {"name": "negative", "type": "CONDITIONING", "link": null, "slot_index": 2},
        {"name": "latent_image", "type": "LATENT", "link": 4, "slot_index": 3}
      ],
      "outputs": [
        {"name": "LATENT", "type": "LATENT", "links": [5], "slot_index": 0}
      ],
      "properties": {"Node name for S&R": "KSampler"},
      "widgets_values": [123456, "randomize", 20, 7.5, "euler", "normal", 1.0],
      "color": "",
      "bgcolor": ""
    }
  ],
  "links": [
    [1, 1, 0, 4, 0, "MODEL"],
    [2, 1, 1, 2, 0, "CLIP"],
    [3, 2, 0, 4, 1, "CONDITIONING"],
    [4, 3, 0, 4, 3, "LATENT"],
    [5, 4, 0, 5, 0, "LATENT"]
  ],
  "groups": [
    {
      "id": 1,
      "bounding": [50, 50, 600, 300],
      "color": "#A15",
      "font_size": 24,
      "flags": {},
      "title": "Generation Pipeline"
    }
  ],
  "config": {},
  "extra": {
    "ds": {
      "scale": 1.0,
      "offset": [0, 0]
    }
  },
  "version": 0.4
}
```

---

## Data Type Reference

Common data types used in node inputs/outputs:

| Type | Description | Typical Source Nodes |
|---|---|---|
| `MODEL` | Diffusion model | CheckpointLoaderSimple, UNETLoader, LoraLoader |
| `CLIP` | CLIP text encoder | CheckpointLoaderSimple, DualCLIPLoader |
| `VAE` | VAE model | CheckpointLoaderSimple, VAELoader |
| `CONDITIONING` | Text conditioning | CLIPTextEncode |
| `LATENT` | Latent image tensor | EmptyLatentImage, VAEEncode |
| `IMAGE` | Pixel image tensor | VAEDecode, LoadImage |
| `MASK` | Mask tensor | EmptyMask, ImageToMask |
| `SAMPLER` | Sampler object | KSamplerSelect |
| `SIGMAS` | Sigma schedule | BasicScheduler |
| `NOISE` | Noise object | Noise_RandomNoise |
| `GUIDER` | Guider object | BasicGuider, CFGGuider |
| `MODEL_PATCHING` | Patched model | IPAdapterApply, ControlNetApply |
| `CONTROL_NET` | ControlNet model | ControlNetLoader |
| `IPADAPTER_MODEL` | IP-Adapter model | IPAdapterModelLoader |
| `CLIP_VISION` | CLIP vision model | CLIPVisionLoader |
| `STYLE_MODEL` | Style model | StyleModelLoader |
| `INT` | Integer value | INTConstant |
| `FLOAT` | Float value | FLOATConstant |
| `STRING` | String value | STRINGConstant |
| `BOOLEAN` | Boolean value | BoolConstant |
| `*` | Wildcard (any type) | Some utility nodes |
