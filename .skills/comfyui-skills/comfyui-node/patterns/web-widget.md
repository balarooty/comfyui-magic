# Custom JavaScript Widget Pattern

## When to Use

Use this pattern when a node needs a **custom UI widget** that goes beyond the built-in controls (text box, number slider, combo dropdown). Common cases:

- Color picker
- Image crop/region selector
- Point coordinate picker on a canvas
- Custom slider with non-linear scale
- Rich text editor
- Drag-and-drop file area

You register a **JS extension** via `app.registerExtension()` and hook into `beforeRegisterNodeDef()` to inject DOM elements and serialization logic.

---

## Complete Python Code

```python
# nodes_color_picker.py

import torch
import numpy as np


class ColorPickerNode:
    """Outputs a solid-color image using a color chosen via a custom JS widget."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "hex_color": ("STRING", {
                    "default": "#FF6600",
                    "tooltip": "Hex color string, managed by the color picker widget"
                }),
                "width": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 4096,
                    "step": 1
                }),
                "height": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 4096,
                    "step": 1
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "generate"
    CATEGORY = "image"

    def generate(self, hex_color: str, width: int, height: int):
        # Parse hex color
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color: #{hex_color}")

        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        # Create solid color image: (batch, height, width, channels)
        img = torch.zeros(1, height, width, 3, dtype=torch.float32)
        img[0, :, :, 0] = r
        img[0, :, :, 1] = g
        img[0, :, :, 2] = b

        return (img,)


class ColorSwatchNode:
    """Displays a color swatch preview from a hex color input."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "hex_color": ("STRING", {"default": "#FF6600"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "swatch"
    CATEGORY = "image"

    def swatch(self, hex_color: str):
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        img = torch.zeros(1, 64, 64, 3, dtype=torch.float32)
        img[0, :, :, 0] = r
        img[0, :, :, 1] = g
        img[0, :, :, 2] = b
        return (img,)


NODE_CLASS_MAPPINGS = {
    "ColorPickerNode": ColorPickerNode,
    "ColorSwatchNode": ColorSwatchNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ColorPickerNode": "Color Picker",
    "ColorSwatchNode": "Color Swatch",
}
```

---

## JavaScript Extension

```javascript
// js/color_picker.js

import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "comfyui.color_picker",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "ColorPickerNode") return;

        // Store original onNodeCreated
        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated
                ? onNodeCreated.apply(this, arguments)
                : undefined;

            // Find the hex_color widget
            const hexWidget = this.widgets.find((w) => w.name === "hex_color");
            if (!hexWidget) return r;

            // Hide the default text widget
            hexWidget.hidden = true;

            // Create a container for our custom widget
            const container = document.createElement("div");
            container.style.cssText = `
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                padding: 8px;
                width: 100%;
                box-sizing: border-box;
            `;

            // Color preview box
            const preview = document.createElement("div");
            preview.style.cssText = `
                width: 100%;
                height: 40px;
                border: 2px solid #555;
                border-radius: 6px;
                background-color: ${hexWidget.value};
                cursor: pointer;
                transition: border-color 0.2s;
            `;
            preview.title = "Click to open color picker";

            // Native HTML color input (hidden, triggered by preview click)
            const colorInput = document.createElement("input");
            colorInput.type = "color";
            colorInput.value = hexWidget.value;
            colorInput.style.cssText = `
                position: absolute;
                visibility: hidden;
                width: 0;
                height: 0;
            `;

            // Hex display + manual entry
            const hexRow = document.createElement("div");
            hexRow.style.cssText = `
                display: flex;
                align-items: center;
                gap: 4px;
                width: 100%;
            `;

            const hexLabel = document.createElement("span");
            hexLabel.textContent = "HEX";
            hexLabel.style.cssText = `
                font-size: 11px;
                color: #aaa;
                font-family: monospace;
                min-width: 28px;
            `;

            const hexInput = document.createElement("input");
            hexInput.type = "text";
            hexInput.value = hexWidget.value;
            hexInput.style.cssText = `
                flex: 1;
                background: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                color: #eee;
                padding: 4px 6px;
                font-family: monospace;
                font-size: 12px;
            `;

            // RGB sliders
            const rgbContainer = document.createElement("div");
            rgbContainer.style.cssText = `
                display: flex;
                flex-direction: column;
                gap: 4px;
                width: 100%;
            `;

            function hexToRgb(hex) {
                hex = hex.replace("#", "");
                return {
                    r: parseInt(hex.substring(0, 2), 16),
                    g: parseInt(hex.substring(2, 4), 16),
                    b: parseInt(hex.substring(4, 6), 16),
                };
            }

            function rgbToHex(r, g, b) {
                return (
                    "#" +
                    [r, g, b]
                        .map((v) =>
                            Math.max(0, Math.min(255, Math.round(v)))
                                .toString(16)
                                .padStart(2, "0")
                        )
                        .join("")
                );
            }

            function createSlider(label, color) {
                const row = document.createElement("div");
                row.style.cssText = `
                    display: flex;
                    align-items: center;
                    gap: 4px;
                `;

                const lbl = document.createElement("span");
                lbl.textContent = label;
                lbl.style.cssText = `
                    font-size: 11px;
                    color: ${color};
                    font-family: monospace;
                    min-width: 14px;
                `;

                const slider = document.createElement("input");
                slider.type = "range";
                slider.min = 0;
                slider.max = 255;
                slider.style.cssText = `
                    flex: 1;
                    height: 12px;
                    cursor: pointer;
                `;

                const val = document.createElement("span");
                val.style.cssText = `
                    font-size: 11px;
                    color: #ccc;
                    font-family: monospace;
                    min-width: 24px;
                    text-align: right;
                `;

                row.appendChild(lbl);
                row.appendChild(slider);
                row.appendChild(val);
                rgbContainer.appendChild(row);

                return { slider, val };
            }

            const rSlider = createSlider("R", "#ff6666");
            const gSlider = createSlider("G", "#66ff66");
            const bSlider = createSlider("B", "#6666ff");

            // Sync everything to the widget
            function syncFromHex(hex) {
                hex = hex.startsWith("#") ? hex : "#" + hex;
                hexWidget.value = hex;
                hexInput.value = hex;
                preview.style.backgroundColor = hex;
                colorInput.value = hex;

                const rgb = hexToRgb(hex);
                rSlider.slider.value = rgb.r;
                rSlider.val.textContent = rgb.r;
                gSlider.slider.value = rgb.g;
                gSlider.val.textContent = rgb.g;
                bSlider.slider.value = rgb.b;
                bSlider.val.textContent = rgb.b;
            }

            function syncFromSliders() {
                const hex = rgbToHex(
                    parseInt(rSlider.slider.value),
                    parseInt(gSlider.slider.value),
                    parseInt(bSlider.slider.value)
                );
                syncFromHex(hex);
            }

            // Event bindings
            preview.addEventListener("click", () => colorInput.click());

            colorInput.addEventListener("input", (e) => {
                syncFromHex(e.target.value);
            });

            hexInput.addEventListener("change", (e) => {
                let val = e.target.value.trim();
                if (!val.startsWith("#")) val = "#" + val;
                if (/^#[0-9a-fA-F]{6}$/.test(val)) {
                    syncFromHex(val);
                } else {
                    hexInput.value = hexWidget.value; // revert
                }
            });

            rSlider.slider.addEventListener("input", syncFromSliders);
            gSlider.slider.addEventListener("input", syncFromSliders);
            bSlider.slider.addEventListener("input", syncFromSliders);

            // Assemble DOM
            hexRow.appendChild(hexLabel);
            hexRow.appendChild(hexInput);

            container.appendChild(preview);
            container.appendChild(hexRow);
            container.appendChild(rgbContainer);

            // Attach to node
            this.addDOMWidget("color_picker", "color-picker", container);

            // Initialize
            syncFromHex(hexWidget.value);

            return r;
        };

        // Serialization: save the widget value when the workflow is exported
        const onSerialize = nodeType.prototype.onSerialize;
        nodeType.prototype.onSerialize = function (info) {
            if (onSerialize) onSerialize.apply(this, arguments);
            const hexWidget = this.widgets.find((w) => w.name === "hex_color");
            if (hexWidget) {
                info.hex_color = hexWidget.value;
            }
        };

        // Deserialization: restore the widget value when the workflow is loaded
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (onConfigure) onConfigure.apply(this, arguments);
            if (info.hex_color) {
                const hexWidget = this.widgets.find(
                    (w) => w.name === "hex_color"
                );
                if (hexWidget) {
                    hexWidget.value = info.hex_color;
                    // Trigger sync after a tick to ensure DOM is ready
                    setTimeout(() => {
                        const event = new Event("change");
                        const hexInput =
                            this.element?.querySelector(
                                'input[type="text"]'
                            );
                        if (hexInput) hexInput.dispatchEvent(event);
                    }, 50);
                }
            }
        };
    },
});
```

---

## Key Concepts

### `app.registerExtension()`

```javascript
app.registerExtension({
    name: "comfyui.my_extension",  // unique identifier
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Called once per node type at startup
    },
});
```

### `beforeRegisterNodeDef()`

Receives the node class prototype before it is registered. You patch methods here:

| Method | Purpose |
|---|---|
| `onNodeCreated` | Called when a node instance is placed on the canvas. Add DOM elements here. |
| `onSerialize` | Called when the workflow is saved. Persist custom widget state. |
| `onConfigure` | Called when a workflow is loaded. Restore custom widget state. |

### `addDOMWidget()`

```javascript
this.addDOMWidget(name, type, element, options);
```

- `name` — unique widget name within the node
- `type` — string identifier (used for CSS styling)
- `element` — a DOM `HTMLElement` to attach
- `options` — optional object with `{ getValue, setValue, onRemove, serialize }`

### Widget Serialization

If your widget stores its value in an existing `INPUT_TYPES` widget (like the `hex_color` STRING above), ComfyUI handles serialization automatically. For fully custom widgets, implement:

```javascript
this.addDOMWidget("my_widget", "my-type", container, {
    getValue() {
        return this._myValue;
    },
    setValue(v) {
        this._myValue = v;
        // update DOM
    },
    serialize: true,  // include in saved workflow
});
```

---

## Key Considerations

| Concern | Guidance |
|---|---|
| **Hidden widget** | Hide the backing widget (`hexWidget.hidden = true`) so it doesn't clutter the UI. Its value is still serialized. |
| **Style scoping** | Use inline styles or a scoped class name to avoid leaking CSS into other nodes. |
| **Event cleanup** | If you add `addEventListener`, consider removing them in an `onRemoved` handler to prevent memory leaks. |
| **`onNodeCreated` chaining** | Always call the original `onNodeCreated` and return its result: `const r = onNodeCreated?.apply(this, arguments); … return r;` |
| **Litegraph canvas** | ComfyUI uses the [litegraph](https://github.com/jagenjo/litegraph.js) library. DOM widgets are rendered in a floating layer above the canvas. Complex widgets may need to handle `pointer-events` carefully. |
| **Mobile / touch** | Test custom widgets on touch devices if your node pack targets them. `input[type="color"]` has inconsistent mobile behavior. |
| **Node size** | Large DOM widgets may overflow the node. Set `this.setSize([width, height])` in `onNodeCreated` if needed. |

---

## Variations

### 1. Image Crop Region Picker

```javascript
// Overlay a canvas on top of an IMAGE preview
// Draw a draggable rectangle
// On change, update crop_x, crop_y, crop_w, crop_h widgets
```

### 2. Point Coordinate Widget

```javascript
// Render a small canvas
// Track click events to set (x, y) coordinates
// Display a crosshair at the selected point
const canvas = document.createElement("canvas");
canvas.width = 256;
canvas.height = 256;
canvas.addEventListener("click", (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * imageWidth;
    const y = ((e.clientY - rect.top) / rect.height) * imageHeight;
    xWidget.value = Math.round(x);
    yWidget.value = Math.round(y);
});
```

### 3. Preset Selector with Preview

```javascript
// Show thumbnails for style presets
// Clicking a thumbnail updates a hidden combo widget
const grid = document.createElement("div");
grid.style.display = "grid";
grid.style.gridTemplateColumns = "repeat(3, 1fr)";
grid.style.gap = "4px";

presets.forEach((preset) => {
    const thumb = document.createElement("img");
    thumb.src = preset.preview;
    thumb.style.cursor = "pointer";
    thumb.addEventListener("click", () => {
        presetWidget.value = preset.name;
    });
    grid.appendChild(thumb);
});
```

### 4. Toggle Switch

```javascript
// Custom boolean toggle with animated switch appearance
const toggle = document.createElement("div");
toggle.className = "custom-toggle";
toggle.addEventListener("click", () => {
    boolWidget.value = !boolWidget.value;
    toggle.classList.toggle("active", boolWidget.value);
});
```
