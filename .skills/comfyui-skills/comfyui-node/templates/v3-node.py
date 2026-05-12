# =============================================================================
# ComfyUI v3 io.ComfyNode Template
# =============================================================================
# The v3 API uses io.ComfyNode as a base class with a declarative schema
# defined via define_schema(). This is the modern, type-safe approach.
#
# Key differences from v1:
#   - Inherits from io.ComfyNode instead of being a plain class
#   - Schema is defined declaratively with io.Schema()
#   - Inputs/outputs use typed io.*.Input and io.*.Output descriptors
#   - execute() is a @classmethod that returns io.NodeOutput()
#   - Built-in support for progress reporting and caching
# =============================================================================

from __future__ import annotations
from typing import Optional

import torch
import numpy as np
from PIL import Image

# The io module is provided by ComfyUI at runtime
# Import it inside the class or at module level — both work
from comfy_api.v3 import io, ui
from comfy_api.v3.files import UploadImage


class MyV3Node(io.ComfyNode):
    """
    A complete v3 io.ComfyNode template.

    Demonstrates:
    - Typed inputs (Image, Float, Int, Boolean, String, Combo, Model, etc.)
    - Typed outputs
    - Schema definition with define_schema()
    - Execution with progress reporting
    - Caching via is_changed / version
    """

    # -------------------------------------------------------------------------
    # Schema definition
    # -------------------------------------------------------------------------

    @classmethod
    def define_schema(cls) -> io.Schema:
        """
        Define the node's inputs, outputs, and metadata.

        This is the v3 equivalent of INPUT_TYPES, RETURN_TYPES, RETURN_NAMES,
        CATEGORY, DESCRIPTION, etc. all in one place.
        """
        return io.Schema(
            # Unique node ID (must be globally unique across all node packs)
            node_id="MyV3Node",

            # Display name in the UI
            display_name="My V3 Node",

            # Category path in the Add Node menu
            category="example/v3",

            # Tooltip description
            description="A template v3 node demonstrating all common input/output types.",

            # Search aliases for the node menu
            search_aliases=["template", "v3 example", "demo"],

            # --- Input definitions ---
            inputs=[
                # Image input
                io.Image.Input(
                    id="image",
                    display_name="Image",
                    tooltip="Input image to process",
                    # optional=False means this input is required (default)
                    optional=False,
                ),

                # Float input with slider
                io.Float.Input(
                    id="strength",
                    display_name="Strength",
                    tooltip="Effect intensity",
                    default=1.0,
                    min=0.0,
                    max=10.0,
                    step=0.01,
                    display=io.FloatDisplay.slider,  # or io.FloatDisplay.number
                ),

                # Integer input
                io.Int.Input(
                    id="iterations",
                    display_name="Iterations",
                    tooltip="Number of processing iterations",
                    default=1,
                    min=1,
                    max=100,
                    step=1,
                    display=io.IntDisplay.number,  # or io.IntDisplay.slider
                ),

                # Boolean input (checkbox)
                io.Boolean.Input(
                    id="enhance",
                    display_name="Enhance",
                    tooltip="Enable enhancement pass",
                    default=False,
                    display=io.BooleanDisplay.toggle,  # or io.BooleanDisplay.checkbox
                ),

                # String input (multiline)
                io.String.Input(
                    id="prompt",
                    display_name="Prompt",
                    tooltip="Text prompt for processing",
                    default="",
                    multiline=True,
                    dynamic_prompts=True,
                    placeholder="Enter your prompt here...",
                ),

                # Combo (dropdown) input
                io.Combo.Input(
                    id="mode",
                    display_name="Mode",
                    tooltip="Processing mode",
                    options=["fast", "quality", "balanced"],
                    default="fast",
                ),

                # Optional mask input
                io.Mask.Input(
                    id="mask",
                    display_name="Mask",
                    tooltip="Optional mask to limit processing area",
                    optional=True,
                ),

                # Float input with number display (optional)
                io.Float.Input(
                    id="bias",
                    display_name="Bias",
                    tooltip="Optional bias offset",
                    default=0.0,
                    min=-1.0,
                    max=1.0,
                    step=0.01,
                    optional=True,
                    display=io.FloatDisplay.number,
                ),
            ],

            # --- Output definitions ---
            outputs=[
                io.Image.Output(
                    id="image",
                    display_name="Image",
                    tooltip="Processed image",
                ),
                io.Mask.Output(
                    id="mask",
                    display_name="Mask",
                    tooltip="Output mask",
                ),
                io.Float.Output(
                    id="factor",
                    display_name="Factor",
                    tooltip="Computed scaling factor",
                ),
            ],

            # --- Optional: Hidden inputs ---
            # These are injected by ComfyUI and not shown as sockets
            hidden=[
                io.Hidden.unique_id,
                io.Hidden.prompt,
                io.Hidden.extra_pnginfo,
            ],

            # --- Optional: Node behavior flags ---
            # is_output_node: True if this is a terminal node (e.g., SaveImage)
            is_output_node=False,

            # is_input_node: True if this is an input node (e.g., LoadImage)
            is_input_node=False,
        )

    # -------------------------------------------------------------------------
    # Caching (optional)
    # -------------------------------------------------------------------------

    @classmethod
    def is_changed(cls, **kwargs) -> float:
        """
        Return a value that changes when the node should re-execute.
        ComfyUI compares this to the cached value to decide whether to
        skip execution and use cached results.

        Return a float timestamp to always re-execute, or compute a hash
        of the relevant inputs.
        """
        import time
        return time.time()

    # Or use a simpler approach with version tracking:
    # version = io.Version(1)  # bump this integer to force re-execution

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    @classmethod
    async def execute(
        cls,
        # --- Inputs (matching the schema IDs) ---
        image: torch.Tensor,
        strength: float,
        iterations: int,
        enhance: bool,
        prompt: str,
        mode: str,
        mask: Optional[torch.Tensor] = None,
        bias: Optional[float] = None,
        # --- Hidden inputs ---
        unique_id: str = "",
        extra_pnginfo: Optional[dict] = None,
        prompt_dict: Optional[dict] = None,
    ) -> io.NodeOutput:
        """
        Execute the node's processing logic.

        This is a classmethod (not an instance method like v1).
        It receives all inputs as keyword arguments matching the schema IDs.

        Args:
            image: Input image tensor [B, H, W, C], values in [0, 1]
            strength: Float parameter controlling effect intensity
            iterations: Integer parameter for repeat count
            enhance: Boolean toggle for enhancement pass
            prompt: String text prompt
            mode: String combo selection
            mask: Optional mask tensor [B, H, W], values in [0, 1]
            bias: Optional float bias value (None if not connected)
            unique_id: This node instance's unique ID (hidden)
            extra_pnginfo: Workflow metadata (hidden)
            prompt_dict: Full prompt dict (hidden)

        Returns:
            io.NodeOutput with outputs matching the schema output order.
            Use io.NodeOutput(value1, value2, ...) or named outputs.
        """
        # --- Access image properties ---
        batch_size, height, width, channels = image.shape
        device = image.device

        # --- Apply processing logic ---
        result = image.clone()

        # Apply strength and iterations
        for i in range(iterations):
            # Report progress for long-running operations
            # ui.PromptServer.instance.send_sync("progress", {
            #     "value": i + 1,
            #     "max": iterations,
            #     "prompt_id": extra_pnginfo.get("prompt_id", "") if extra_pnginfo else "",
            # })

            result = result * strength + (bias or 0.0)

        # Clamp to valid range
        result = torch.clamp(result, 0.0, 1.0)

        # Apply enhancement if enabled
        if enhance:
            # Example: simple contrast enhancement
            mean_val = result.mean()
            result = torch.clamp((result - mean_val) * 1.2 + mean_val, 0.0, 1.0)

        # Handle optional mask
        if mask is not None:
            if mask.dim() == 3:
                mask = mask.unsqueeze(-1)
            result = result * mask + image * (1 - mask)
        else:
            mask = torch.ones(batch_size, height, width, device=device)

        # Compute output factor
        factor = strength * iterations

        # --- Return outputs in schema order ---
        return io.NodeOutput(result, mask.squeeze(-1), factor)


# =============================================================================
# v3 Advanced Patterns
# =============================================================================

# --- Pattern: File upload input ---
# class UploadNode(io.ComfyNode):
#     @classmethod
#     def define_schema(cls):
#         return io.Schema(
#             node_id="UploadNode",
#             display_name="Upload Node",
#             category="example",
#             inputs=[
#                 UploadImage.Input(
#                     id="image",
#                     display_name="Image",
#                     image_upload=True,
#                 ),
#             ],
#             outputs=[io.Image.Output(id="image", display_name="Image")],
#         )
#
#     @classmethod
#     async def execute(cls, image: torch.Tensor) -> io.NodeOutput:
#         return io.NodeOutput(image)


# --- Pattern: Custom widget via JavaScript ---
# class WidgetNode(io.ComfyNode):
#     @classmethod
#     def define_schema(cls):
#         return io.Schema(
#             node_id="WidgetNode",
#             display_name="Widget Node",
#             category="example",
#             inputs=[
#                 io.String.Input(
#                     id="text",
#                     display_name="Text",
#                     widget=io.WidgetType.textarea,
#                 ),
#             ],
#             outputs=[io.String.Output(id="text", display_name="Text")],
#         )
#
#     @classmethod
#     async def execute(cls, text: str) -> io.NodeOutput:
#         return io.NodeOutput(text)


# --- Pattern: Node with version for caching ---
# class VersionedNode(io.ComfyNode):
#     version = io.Version(2)  # bump to invalidate cache
#
#     @classmethod
#     def define_schema(cls):
#         return io.Schema(
#             node_id="VersionedNode",
#             display_name="Versioned Node",
#             category="example",
#             inputs=[io.Image.Input(id="image")],
#             outputs=[io.Image.Output(id="image")],
#         )
#
#     @classmethod
#     async def execute(cls, image: torch.Tensor) -> io.NodeOutput:
#         return io.NodeOutput(image)


# =============================================================================
# Node Registration (in __init__.py)
# =============================================================================
# For v3 nodes, registration is automatic if using the io.ComfyNode pattern.
# However, you can still register manually:
#
#   from .v3_node import MyV3Node
#   NODE_CLASS_MAPPINGS = {"MyV3Node": MyV3Node}
#   NODE_DISPLAY_NAME_MAPPINGS = {"MyV3Node": "My V3 Node"}
#
# =============================================================================
