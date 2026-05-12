// =============================================================================
// ComfyUI Web Extension Template
// =============================================================================
// JavaScript extensions customize the ComfyUI frontend. They can:
//   - Add custom widgets to nodes
//   - Modify node behavior (inputs, outputs, rendering)
//   - Add UI elements (menus, buttons, dialogs)
//   - Communicate with the backend via API calls
//   - Hook into the graph editor lifecycle
//
// This file should be placed in the web/ directory of your custom node pack.
// ComfyUI automatically loads all .js files from WEB_DIRECTORY.
//
// Key APIs:
//   app.registerExtension()  - Register an extension with hooks
//   LiteGraph               - The graph editor library
//   ComfyApp                - The main application instance
//   api                     - API client for backend communication
// =============================================================================

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// =============================================================================
// Extension Registration
// =============================================================================

app.registerExtension({
    // Unique ID for this extension
    name: "my.custom.extension",

    // -------------------------------------------------------------------------
    // Hook: beforeRegisterNodeDef
    // -------------------------------------------------------------------------
    // Called when a node type definition is being registered.
    // Use this to modify the node's prototype before any instances are created.
    // This is where you add custom widgets, modify inputs/outputs, etc.
    //
    // Parameters:
    //   nodeType - the node class constructor
    //   nodeData - the node definition from Python (inputs, outputs, etc.)
    // -------------------------------------------------------------------------

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Only modify our specific node
        if (nodeData.name === "MyV3Node" || nodeData.name === "MyLegacyNode") {

            // --- Add custom widgets on node creation ---
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                // Call the original onNodeCreated if it exists
                const result = onNodeCreated?.apply(this, arguments);

                // Add a custom button widget
                this.addWidget("button", "Refresh", "refresh", () => {
                    console.log("[MyExtension] Refresh button clicked");
                    // Trigger a backend API call or custom logic
                    this.refreshData?.();
                });

                // Add a custom text widget (read-only info display)
                this.infoWidget = this.addWidget("text", "Status", "Ready", (v) => {
                    // This widget is display-only, ignore user edits
                }, { readOnly: true });

                // Add a custom combo widget
                this.addWidget("combo", "Theme", "dark", (v) => {
                    console.log("[MyExtension] Theme changed to:", v);
                    this._theme = v;
                }, { values: ["dark", "light", "auto"] });

                return result;
            };

            // --- Modify the node's execution behavior ---
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                const result = onExecuted?.apply(this, arguments);

                // Update our custom widget with output data
                if (this.infoWidget && message?.text) {
                    this.infoWidget.value = message.text[0] || "Done";
                }

                return result;
            };

            // --- Add extra menu options ---
            const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
            nodeType.prototype.getExtraMenuOptions = function (_, options) {
                getExtraMenuOptions?.apply(this, arguments);

                options.push({
                    content: "🔄 Reset Node",
                    callback: () => {
                        // Reset all widget values to defaults
                        this.widgets?.forEach((w) => {
                            if (w.name === "strength") w.value = 1.0;
                            if (w.name === "iterations") w.value = 1;
                        });
                        this.setDirtyCanvas(true, true);
                    },
                });

                options.push(null); // separator

                options.push({
                    content: "📋 Copy Config",
                    callback: () => {
                        const config = {};
                        this.widgets?.forEach((w) => {
                            config[w.name] = w.value;
                        });
                        navigator.clipboard.writeText(JSON.stringify(config, null, 2));
                        console.log("[MyExtension] Config copied to clipboard");
                    },
                });
            };
        }
    },

    // -------------------------------------------------------------------------
    // Hook: nodeCreated
    // -------------------------------------------------------------------------
    // Called after a node instance is created and added to the graph.
    // Use this for per-instance setup that depends on the node being in the graph.
    // -------------------------------------------------------------------------

    nodeCreated(node) {
        if (node.type === "MyV3Node" || node.type === "MyLegacyNode") {
            console.log("[MyExtension] Node created:", node.id, node.type);

            // Example: set a custom color
            // node.color = "#2a363b";
            // node.bgcolor = "#1a262b";

            // Example: store custom data on the node
            node._myCustomData = { created: Date.now() };
        }
    },

    // -------------------------------------------------------------------------
    // Hook: setup
    // -------------------------------------------------------------------------
    // Called once when the extension is loaded. Use this for one-time setup
    // like registering global event handlers, adding UI elements, etc.
    // -------------------------------------------------------------------------

    setup() {
        console.log("[MyExtension] Extension loaded");

        // Example: register a keyboard shortcut
        // document.addEventListener("keydown", (e) => {
        //     if (e.ctrlKey && e.shiftKey && e.key === "M") {
        //         console.log("[MyExtension] Custom shortcut triggered");
        //     }
        // });

        // Example: add a custom menu item to the main menu
        // const menu = document.querySelector(".comfy-menu");
        // if (menu) {
        //     const btn = document.createElement("button");
        //     btn.textContent = "My Extension";
        //     btn.onclick = () => alert("Hello from MyExtension!");
        //     menu.appendChild(btn);
        // }

        // Example: listen for graph load events
        // app.graph.addEventListener("change", () => {
        //     console.log("[MyExtension] Graph changed");
        // });
    },

    // -------------------------------------------------------------------------
    // Hook: beforeConfigureGraph
    // -------------------------------------------------------------------------
    // Called before a workflow/graph is loaded. Use this to preprocess
    // workflow data or handle version migration.
    // -------------------------------------------------------------------------

    // beforeConfigureGraph(graphData) {
    //     console.log("[MyExtension] Loading workflow...");
    // },

    // -------------------------------------------------------------------------
    // Hook: afterConfigureGraph
    // -------------------------------------------------------------------------
    // Called after a workflow/graph is loaded. Use this for post-load setup.
    // -------------------------------------------------------------------------

    // afterConfigureGraph(graphData) {
    //     console.log("[MyExtension] Workflow loaded");
    // },
});


// =============================================================================
// Advanced: Server-Client Communication
// =============================================================================

// --- Sending data TO the server (from client) ---
// async function sendToServer(endpoint, data) {
//     try {
//         const response = await api.fetchApi(`/my_custom_api/${endpoint}`, {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify(data),
//         });
//         return await response.json();
//     } catch (err) {
//         console.error("[MyExtension] API error:", err);
//         throw err;
//     }
// }

// --- Receiving data FROM the server (websocket) ---
// You need to register an API route on the Python side.
//
// Python side (in your __init__.py or a separate routes file):
//   from server import PromptServer
//   from aiohttp import web
//
//   @PromptServer.instance.routes.post("/my_custom_api/hello")
//   async def handle_hello(request):
//       data = await request.json()
//       return web.json_response({"status": "ok", "echo": data})
//
//   # Send data to client via websocket
//   PromptServer.instance.send_sync("my.custom.event", {"data": "hello"}, client_id)

// JS side to listen for websocket events:
// api.addEventListener("my.custom.event", (event) => {
//     const data = event.detail;
//     console.log("[MyExtension] Received from server:", data);
// });


// =============================================================================
// Advanced: Custom Widget Type
// =============================================================================

// Register a completely custom widget type with full rendering control.
//
// function createMyCustomWidget(node, inputName, inputData, widgetConfig) {
//     const widget = {
//         name: inputName,
//         type: "my_custom_widget",
//         value: widgetConfig.default || 0,
//         y: 0,
//         options: widgetConfig,
//
//         // Called to compute the widget's height
//         computeSize(width) {
//             return [width, 30]; // [width, height]
//         },
//
//         // Called to draw the widget on canvas
//         draw(ctx, node, width, y, height) {
//             ctx.fillStyle = "#1a1a2e";
//             ctx.fillRect(0, y, width, height);
//
//             ctx.fillStyle = "#e0e0e0";
//             ctx.font = "12px monospace";
//             ctx.fillText(`${this.name}: ${this.value}`, 8, y + height / 2 + 4);
//         },
//
//         // Called on mouse events
//         mouse(event, pos, node) {
//             if (event.type === "pointerdown") {
//                 this.value = (this.value + 1) % 10;
//                 return true; // consume the event
//             }
//             return false;
//         },
//     };
//
//     node.addCustomWidget(widget);
//     return widget;
// }
//
// // Then in beforeRegisterNodeDef:
// if (nodeData.name === "MyNode") {
//     const onNodeCreated = nodeType.prototype.onNodeCreated;
//     nodeType.prototype.onNodeCreated = function () {
//         const result = onNodeCreated?.apply(this, arguments);
//         createMyCustomWidget(this, "my_widget", {}, { default: 0 });
//         return result;
//     };
// }
