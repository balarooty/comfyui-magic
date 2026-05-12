# Web Extensions Reference

JavaScript extension patterns for custom UI in ComfyUI nodes.

## WEB_DIRECTORY Setup

In your `__init__.py`, export the path to your JavaScript extensions:

```python
WEB_DIRECTORY = "./web/js"
```

Directory structure:
```
MyNodePack/
├── __init__.py
├── nodes.py
└── web/
    └── js/
        └── my_extension.js
```

## app.registerExtension()

The primary API for registering JavaScript extensions with ComfyUI.

```javascript
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "my.custom.extension",
    async setup() {
        // Called when ComfyUI is fully loaded
        console.log("Extension loaded");
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Called before each node type is registered
    },
    nodeCreated(node) {
        // Called when a node instance is created on the canvas
    },
});
```

## Available Hooks

### setup

Called once when ComfyUI finishes loading.

```javascript
app.registerExtension({
    name: "my.extension",
    async setup() {
        // Initialize resources
        console.log("ComfyUI loaded, extension ready");

        // Add global event listeners
        app.canvasEl.addEventListener("click", (e) => {
            // Handle canvas clicks
        });
    },
});
```

### beforeRegisterNodeDef

Called before each node type is registered. Allows modifying the node definition.

```javascript
app.registerExtension({
    name: "my.extension",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // nodeType: the node class constructor
        // nodeData: the node definition from Python

        if (nodeData.name === "MyNode") {
            // Modify the node definition
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);
                // Custom initialization
                this.addWidget("text", "custom_widget", "", () => {});
            };
        }
    },
});
```

### nodeCreated

Called when a node instance is created on the canvas.

```javascript
app.registerExtension({
    name: "my.extension",
    nodeCreated(node) {
        if (node.type === "MyNode") {
            // Add custom widgets
            const widget = node.addWidget("text", "info", "", () => {}, {});

            // Modify node appearance
            node.color = "#2a363b";
            node.bgcolor = "#333";
        }
    },
});
```

### afterConfigureGraph

Called after a workflow is loaded.

```javascript
app.registerExtension({
    name: "my.extension",
    afterConfigureGraph() {
        // Workflow has been loaded
        console.log("Graph configured");
    },
});
```

### beforeConfigureGraph

Called before a workflow is loaded.

```javascript
app.registerExtension({
    name: "my.extension",
    beforeConfigureGraph() {
        // Cleanup before loading new workflow
        console.log("Loading new graph");
    },
});
```

### nodeMoved

Called when a node is moved on the canvas.

```javascript
app.registerExtension({
    name: "my.extension",
    nodeMoved(node) {
        if (node.type === "MyNode") {
            console.log(`Node moved to ${node.pos}`);
        }
    },
});
```

## Modifying Node Definitions

Customize node behavior before registration.

```javascript
app.registerExtension({
    name: "my.extension",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "KSampler") {
            // Add extra widgets
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Add a custom widget
                this.addWidget("toggle", "advanced_mode", false, (value) => {
                    // Toggle advanced inputs visibility
                    this.inputs.forEach((input) => {
                        if (input.name.startsWith("advanced_")) {
                            input.hidden = !value;
                        }
                    });
                });

                return result;
            };
        }
    },
});
```

## Adding Custom Widgets

### Text Widget

```javascript
const widget = node.addWidget("text", "widget_name", "default_value", (value) => {
    console.log("Text changed:", value);
}, {});
```

### Number Widget

```javascript
const widget = node.addWidget("number", "widget_name", 0, (value) => {
    console.log("Number changed:", value);
}, { min: 0, max: 100, step: 1 });
```

### Toggle Widget

```javascript
const widget = node.addWidget("toggle", "widget_name", false, (value) => {
    console.log("Toggle changed:", value);
});
```

### Combo Widget

```javascript
const widget = node.addWidget("combo", "widget_name", "option1", (value) => {
    console.log("Combo changed:", value);
}, { values: ["option1", "option2", "option3"] });
```

### Button Widget

```javascript
const widget = node.addWidget("button", "click_me", "Click Me", () => {
    console.log("Button clicked!");
});
```

## Canvas-Based Editors

Create custom canvas-based editors for node inputs.

```javascript
app.registerExtension({
    name: "my.canvas.editor",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MaskEditor") {
            nodeType.prototype.onNodeCreated = function () {
                const canvas = document.createElement("canvas");
                canvas.width = 512;
                canvas.height = 512;
                canvas.style.border = "1px solid #555";

                const ctx = canvas.getContext("2d");
                ctx.fillStyle = "black";
                ctx.fillRect(0, 0, 512, 512);

                // Drawing state
                let isDrawing = false;
                let lastX = 0;
                let lastY = 0;

                canvas.addEventListener("mousedown", (e) => {
                    isDrawing = true;
                    [lastX, lastY] = [e.offsetX, e.offsetY];
                });

                canvas.addEventListener("mousemove", (e) => {
                    if (!isDrawing) return;
                    ctx.strokeStyle = "white";
                    ctx.lineWidth = 10;
                    ctx.lineCap = "round";
                    ctx.beginPath();
                    ctx.moveTo(lastX, lastY);
                    ctx.lineTo(e.offsetX, e.offsetY);
                    ctx.stroke();
                    [lastX, lastY] = [e.offsetX, e.offsetY];
                });

                canvas.addEventListener("mouseup", () => {
                    isDrawing = false;
                });

                // Add canvas as DOM widget
                this.addDOMWidget("mask_canvas", "canvas", canvas, {
                    serialize: () => canvas.toDataURL(),
                });
            };
        }
    },
});
```

## Server→Client Sync

Send data from server to client using `PromptServer.instance.send_sync()`.

### Python Server Side

```python
from server import PromptServer

class MyNode:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"image": ("IMAGE",)}}

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    OUTPUT_NODE = True  # Required for UI updates

    def process(self, image):
        # Process image
        result = image * 1.5

        # Send data to client
        PromptServer.instance.send_sync("my.custom.event", {
            "node_id": self.unique_id,
            "data": {"status": "complete", "info": "Processing done"},
        })

        return (result,)
```

### JavaScript Client Side

```javascript
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "my.sync.extension",
    setup() {
        // Listen for server events
        api.addEventListener("my.custom.event", (event) => {
            const { node_id, data } = event.detail;
            console.log(`Node ${node_id}:`, data);

            // Update node UI
            const node = app.graph.getNodeById(node_id);
            if (node) {
                // Update a widget
                const widget = node.widgets?.find((w) => w.name === "status");
                if (widget) {
                    widget.value = data.status;
                }
            }
        });
    },
});
```

## Client→Server Communication

Send data from client to server using `app.api`.

```javascript
// Send a custom API request
async function sendToServer(endpoint, data) {
    const response = await api.fetchApi(`/my_custom_endpoint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    return response.json();
}
```

### Python Server Endpoint

```python
from server import PromptServer
from aiohttp import web

@PromptServer.instance.routes.post("/my_custom_endpoint")
async def my_endpoint(request):
    data = await request.json()
    # Process data
    return web.json_response({"status": "ok", "result": data})
```

## Dynamic Input Management

Add or remove inputs dynamically.

```javascript
app.registerExtension({
    name: "my.dynamic.inputs",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DynamicInputNode") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Add button to add new inputs
                const addBtn = this.addWidget("button", "add_input", "Add Input", () => {
                    const inputName = `input_${this.inputs.length}`;
                    this.addInput(inputName, "*");
                    this.setSize(this.computeSize());
                });

                // Add button to remove last input
                const removeBtn = this.addWidget("button", "remove_input", "Remove Input", () => {
                    if (this.inputs.length > 1) {
                        this.removeInput(this.inputs.length - 1);
                        this.setSize(this.computeSize());
                    }
                });

                return result;
            };
        }
    },
});
```

## Custom Context Menus

Add custom right-click menu items.

```javascript
app.registerExtension({
    name: "my.context.menu",
    setup() {
        // Add to canvas context menu
        const origGetCanvasMenuOptions = LGraphCanvas.prototype.getCanvasMenuOptions;
        LGraphCanvas.prototype.getCanvasMenuOptions = function () {
            const options = origGetCanvasMenuOptions.apply(this, arguments);

            options.push(null); // Separator
            options.push({
                content: "My Custom Action",
                callback: () => {
                    console.log("Custom action triggered");
                },
            });

            return options;
        };

        // Add to node context menu
        const origGetNodeMenuOptions = LGraphCanvas.prototype.getNodeMenuOptions;
        LGraphCanvas.prototype.getNodeMenuOptions = function (node) {
            const options = origGetNodeMenuOptions.apply(this, arguments);

            if (node.type === "MyNode") {
                options.push(null);
                options.push({
                    content: "Node-specific Action",
                    callback: () => {
                        console.log(`Action on node ${node.id}`);
                    },
                });
            }

            return options;
        };
    },
});
```

## CSS Styling for Nodes

Add custom CSS for node styling.

```javascript
app.registerExtension({
    name: "my.css.extension",
    setup() {
        const style = document.createElement("style");
        style.textContent = `
            /* Style specific node types */
            .litegraph .node.MyNode {
                border-radius: 8px;
            }

            /* Custom widget styling */
            .my-custom-widget {
                background: #2a2a2a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                color: #ddd;
            }

            /* Status indicators */
            .node-status-processing {
                border-left: 3px solid #4CAF50;
            }

            .node-status-error {
                border-left: 3px solid #f44336;
            }
        `;
        document.head.appendChild(style);
    },
});
```

## Complete Extension Example

```javascript
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "my.complete.extension",

    async setup() {
        console.log("[MyExtension] Loaded");

        // Listen for server events
        api.addEventListener("my.progress.update", (event) => {
            const { node_id, progress, total } = event.detail;
            const node = app.graph.getNodeById(node_id);
            if (node) {
                const pct = Math.round((progress / total) * 100);
                node.title = `Processing: ${pct}%`;
            }
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MyProcessor") {
            // Add custom initialization
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Add progress bar widget
                this.addWidget("text", "status", "Ready", () => {}, { readonly: true });

                // Add batch size control
                this.addWidget("number", "batch_size", 1, () => {}, {
                    min: 1,
                    max: 32,
                    step: 1,
                });

                return result;
            };

            // Override serialization to save custom widget values
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function (info) {
                onSerialize?.apply(this, arguments);
                info.batch_size = this.widgets?.find((w) => w.name === "batch_size")?.value;
            };

            // Override deserialization to restore custom widget values
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                onConfigure?.apply(this, arguments);
                if (info.batch_size !== undefined) {
                    const widget = this.widgets?.find((w) => w.name === "batch_size");
                    if (widget) widget.value = info.batch_size;
                }
            };
        }
    },

    nodeCreated(node) {
        if (node.type === "MyProcessor") {
            // Style the node
            node.color = "#1a1a2e";
            node.bgcolor = "#16213e";

            // Add custom title bar
            node.title = "My Processor";
        }
    },
});
```

## Minimal Extension Template

```javascript
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "my.minimal.extension",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MyNode") {
            nodeType.prototype.onNodeCreated = function () {
                // Custom initialization here
            };
        }
    },
});
```
