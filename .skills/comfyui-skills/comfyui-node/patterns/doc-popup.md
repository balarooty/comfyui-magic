# JS Documentation Popup Pattern

## When to Use

- Your custom node has complex behavior that doesn't fit in the tiny tooltip.
- You want to provide usage instructions, parameter explanations, or examples directly in the UI.
- You want a consistent "?" help button on all your nodes.

## Problem

ComfyUI shows `nodeData.description` as a brief tooltip on hover. There's no built-in way to display rich documentation, markdown, or multi-paragraph guides inside the node graph.

## Solution: `beforeRegisterNodeDef` + JS Extension

Intercept `nodeData.description` in a JS extension's `beforeRegisterNodeDef` hook and inject a "?" button that opens a resizable popup with rendered Markdown.

### Python — Set Descriptions

```python
# my_node.py

class DetailedUpscaler:
    """Upscale an image with detailed control over denoise and tile size."""

    DESCRIPTION = """
## Detailed Upscaler

Upscales images using a model with optional denoise pass.

### Parameters
- **upscale_model**: The upscaling model (e.g. RealESRGAN_x4plus)
- **image**: Input image tensor
- **scale_factor**: Multiplier for output resolution (1.0–8.0)
- **denoise_strength**: How much to denoise during upscale (0.0 = none, 1.0 = max)
- **tile_size**: Pixels per tile. Lower = less VRAM, slower. 0 = auto.

### Tips
- Use `scale_factor=2` for quick previews.
- Set `denoise_strength=0.0` for photo-realistic upscaling.
- For very large images, set `tile_size=512` to avoid OOM.

### Example Workflow
```
LoadImage → DetailedUpscaler (x2, denoise=0.2) → SaveImage
```
"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "upscale_model": ("UPSCALE_MODEL",),
                "image": ("IMAGE",),
                "scale_factor": ("FLOAT", {"default": 2.0, "min": 1.0, "max": 8.0, "step": 0.1}),
                "denoise_strength": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "tile_size": ("INT", {"default": 0, "min": 0, "max": 2048, "step": 64}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"
    CATEGORY = "image/upscaling"

    def execute(self, upscale_model, image, scale_factor, denoise_strength, tile_size):
        import comfy.utils
        samples = image.movedim(-1, -3)
        output = upscale_model(samples, tile_size=tile_size if tile_size > 0 else None)
        result = output.movedim(-3, -1)
        return (result,)
```

### JavaScript — Extension with Popup

Save as `web/doc_popup.js` in your custom node directory.

```javascript
// web/doc_popup.js

import { app } from "../../scripts/app.js";

const HELP_BUTTON_SIZE = 20;
const POPUP_MIN_WIDTH = 300;
const POPUP_MIN_HEIGHT = 200;
const POPUP_DEFAULT_WIDTH = 450;
const POPUP_DEFAULT_HEIGHT = 400;

// Minimal Markdown → HTML renderer (no external deps)
function renderMarkdown(md) {
    let html = md
        // Code blocks
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Headers
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bold and italic
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Unordered lists
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        // Links
        .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Paragraphs (double newline)
        .replace(/\n{2,}/g, '</p><p>')
        // Single newlines to <br>
        .replace(/\n/g, '<br>');

    // Wrap loose <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    // Clean up nested <ul>
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    return `<p>${html}</p>`;
}

// Create the popup element
function createDocPopup(title, markdownContent) {
    const overlay = document.createElement("div");
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.4); z-index: 10000;
        display: flex; align-items: center; justify-content: center;
    `;

    const popup = document.createElement("div");
    popup.style.cssText = `
        background: #1e1e2e; color: #cdd6f4; border: 1px solid #585b70;
        border-radius: 8px; width: ${POPUP_DEFAULT_WIDTH}px;
        height: ${POPUP_DEFAULT_HEIGHT}px; min-width: ${POPUP_MIN_WIDTH}px;
        min-height: ${POPUP_MIN_HEIGHT}px; display: flex; flex-direction: column;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5); resize: both; overflow: hidden;
    `;

    // Header
    const header = document.createElement("div");
    header.style.cssText = `
        padding: 10px 14px; background: #313244; cursor: move;
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #585b70; font-weight: bold; font-size: 14px;
    `;
    header.textContent = title;

    const closeBtn = document.createElement("span");
    closeBtn.textContent = "✕";
    closeBtn.style.cssText = `cursor: pointer; padding: 0 4px; font-size: 16px;`;
    closeBtn.onclick = () => overlay.remove();
    header.appendChild(closeBtn);

    // Content
    const content = document.createElement("div");
    content.style.cssText = `
        padding: 16px; overflow: auto; flex: 1; font-size: 13px;
        line-height: 1.6; font-family: -apple-system, sans-serif;
    `;
    content.innerHTML = renderMarkdown(markdownContent);

    // Style injected elements
    const style = document.createElement("style");
    style.textContent = `
        .doc-popup-content h1 { font-size: 18px; margin: 0 0 8px; color: #f5c2e7; }
        .doc-popup-content h2 { font-size: 16px; margin: 12px 0 6px; color: #89b4fa; }
        .doc-popup-content h3 { font-size: 14px; margin: 10px 0 4px; color: #a6e3a1; }
        .doc-popup-content code { background: #313244; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
        .doc-popup-content pre { background: #181825; padding: 10px; border-radius: 6px; overflow-x: auto; }
        .doc-popup-content pre code { background: none; padding: 0; }
        .doc-popup-content ul { margin: 4px 0; padding-left: 20px; }
        .doc-popup-content li { margin: 2px 0; }
        .doc-popup-content a { color: #89b4fa; }
        .doc-popup-content p { margin: 6px 0; }
    `;
    content.appendChild(style);
    content.classList.add("doc-popup-content");

    popup.appendChild(header);
    popup.appendChild(content);
    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Drag support
    let isDragging = false, offsetX, offsetY;
    header.onmousedown = (e) => {
        isDragging = true;
        offsetX = e.clientX - popup.offsetLeft;
        offsetY = e.clientY - popup.offsetTop;
    };
    document.onmousemove = (e) => {
        if (!isDragging) return;
        popup.style.left = (e.clientX - offsetX) + "px";
        popup.style.top = (e.clientY - offsetY) + "px";
        popup.style.position = "fixed";
    };
    document.onmouseup = () => isDragging = false;

    // Close on overlay click (not popup)
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
}

// Hook into ComfyUI node registration
app.registerExtension({
    name: "my_node.doc_popup",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const description = nodeData.description;
        if (!description || !description.trim()) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated?.apply(this, arguments);

            // Add the "?" help button to the node title
            const helpBtn = this.addWidget("button", "?", null, () => {
                createDocPopup(nodeData.name, description);
            });
            helpBtn.computeSize = () => [HELP_BUTTON_SIZE, HELP_BUTTON_SIZE];
            helpBtn.serialize = false;

            return r;
        };
    },
});
```

**`__init__.py` — Register the JS extension:**

```python
WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {"DetailedUpscaler": DetailedUpscaler}
NODE_DISPLAY_NAME_MAPPINGS = {"DetailedUpscaler": "Detailed Upscaler"}
```

## Key Considerations

1. **`DESCRIPTION` vs docstring** — ComfyUI reads `nodeData.description` from the class `DESCRIPTION` attribute (preferred) or the docstring. Use `DESCRIPTION` for explicit control.
2. **`beforeRegisterNodeDef`** — This hook fires once per node type during extension registration. It's the correct place to modify `nodeType.prototype`.
3. **No external dependencies** — The minimal Markdown renderer avoids pulling in `marked`, `markdown-it`, etc. If you need full GFM, bundle a library.
4. **`addWidget` placement** — The button appears at the bottom of the node. For title-bar placement, override `onDrawForeground` instead.
5. **CSS scoping** — Inject `<style>` inside the popup container, or use unique class names, to avoid polluting the global Litegraph CSS.
6. **Cleanup** — Remove the overlay from the DOM when closed to prevent memory leaks on long sessions.
7. **`WEB_DIRECTORY`** — Must be declared at module level in `__init__.py`. ComfyUI auto-loads all `.js` files in that directory.
