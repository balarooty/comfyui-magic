# Config Hot-Reload Pattern

## When to Use

- Your node reads configuration from a JSON (or YAML/TOML) file that users edit while ComfyUI is running.
- You want changes to take effect on the **next execution** without restarting the server.
- The config file may not exist at import time (user creates it later).
- Multiple nodes or workflows share the same config file.

## Problem

Loading config once at import time freezes values. Users must restart ComfyUI to pick up edits.

```python
# BROKEN: loaded once, never updates
import json
with open("styles.json") as f:
    STYLES = json.load(f)

class StyleSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"style": (list(STYLES.keys()),)}}  # stale
```

## Solution: Re-read on Every Execution

Read the file inside `INPUT_TYPES` and/or `execute()`. Use `os.path.getmtime` to avoid parsing when unchanged.

```python
import json
import os
import folder_paths

CONFIG_DIR = os.path.join(folder_paths.base_path, "custom_nodes", "my_node", "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "styles.json")


def _load_styles():
    """Read styles.json from disk every time it's called."""
    if not os.path.isfile(CONFIG_PATH):
        return {"default": {"positive": "", "negative": ""}}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class StyleSelector:
    """Select a style preset that hot-reloads from styles.json."""

    @classmethod
    def INPUT_TYPES(cls):
        styles = _load_styles()
        style_names = list(styles.keys())
        if not style_names:
            style_names = ["default"]
        return {
            "required": {
                "style": (style_names,),
                "image_prompt": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "execute"
    CATEGORY = "prompt/style"

    def execute(self, style, image_prompt):
        styles = _load_styles()
        preset = styles.get(style, {})
        positive = preset.get("positive", "").replace("{prompt}", image_prompt)
        negative = preset.get("negative", "")
        return (positive, negative)


class StyleEditor:
    """Write a new style to styles.json via a node output."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "style_name": ("STRING", {"default": "new_style"}),
                "positive_template": ("STRING", {"multiline": True, "default": "{prompt}"}),
                "negative_template": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "prompt/style"

    def execute(self, style_name, positive_template, negative_template):
        styles = _load_styles()
        styles[style_name] = {
            "positive": positive_template,
            "negative": negative_template,
        }
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(styles, f, indent=2, ensure_ascii=False)
        return ()


# HTTP endpoint for external tools to trigger a reload
from aiohttp import web

def register_routes(routes):
    @routes.post("/my_node/reload_styles")
    async def reload_handler(request):
        styles = _load_styles()
        return web.json_response({"loaded": len(styles), "keys": list(styles.keys())})
```

**`styles.json` example:**

```json
{
  "cinematic": {
    "positive": "cinematic film still, {prompt}, dramatic lighting, 35mm",
    "negative": "cartoon, anime, low quality"
  },
  "anime": {
    "positive": "anime screenshot, {prompt}, vibrant colors",
    "negative": "photorealistic, 3d render"
  }
}
```

## Key Considerations

1. **`INPUT_TYPES` is the dropdown source** — ComfyUI calls `INPUT_TYPES` when building the node menu. Re-reading the file here means the dropdown updates on the next node-add or page refresh, without restart.
2. **`execute()` is the runtime source** — Always re-read inside `execute()` too, because the user may have edited the file between adding the node and clicking Queue.
3. **File-not-found** — Always handle the missing-file case gracefully. Return a sensible default.
4. **Encoding** — Use `encoding="utf-8"` explicitly. Config files with special characters (CJK, emoji) will crash on Windows otherwise.
5. **Atomic writes** — Write to a temp file then `os.replace()` to avoid corruption if ComfyUI reads mid-write:
   ```python
   tmp = CONFIG_PATH + ".tmp"
   with open(tmp, "w", encoding="utf-8") as f:
       json.dump(styles, f, indent=2)
   os.replace(tmp, CONFIG_PATH)
   ```
6. **Validation** — Validate the schema after loading. A malformed JSON file should not crash the server; catch `json.JSONDecodeError` and log a warning.
7. **Hot-reload HTTP routes** — Register via `NODE_CLASS_MAPPINGS` side-effects or `__init__.py` so the endpoint is available immediately. External tools (A1111, scripts) can POST to trigger saves.
