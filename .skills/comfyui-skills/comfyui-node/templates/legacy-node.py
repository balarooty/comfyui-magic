# =============================================================================
# ComfyUI Legacy v1 Custom Node Template
# =============================================================================
# This is the traditional (v1) node format used by most ComfyUI custom nodes.
# Nodes are plain Python classes with specific class attributes and methods.
#
# Key attributes:
#   INPUT_TYPES   - classmethod defining input sockets (required, optional, hidden)
#   RETURN_TYPES  - tuple of output type strings
#   RETURN_NAMES  - tuple of output socket display names
#   FUNCTION      - name of the method to call (usually "execute")
#   CATEGORY      - node menu category (supports "/" for submenus)
#   DESCRIPTION   - tooltip text shown on hover
#   OUTPUT_NODE   - True if this is a terminal/output node (no downstream connections)
#   INPUT_IS_LIST - True if inputs should be passed as lists (batch processing)
#   OUTPUT_IS_LIST - True if outputs are lists
#   SEARCH_ALIASES - list of alternate search terms for the node menu
# =============================================================================

from typing import Any
import torch
import numpy as np
from PIL import Image


class MyLegacyNode:
    """
    A complete legacy v1 ComfyUI custom node template.

    This node demonstrates all common patterns including:
    - Required, optional, and hidden inputs
    - Multiple output types
    - Input validation
    - Change detection for caching
    - List/batch processing modes
    """

    # -------------------------------------------------------------------------
    # Node metadata
    # -------------------------------------------------------------------------

    # Display name shown in the node title bar and search menu
    # If omitted, the class name is used
    # (not shown here as a class attr — set via __init__.py mappings instead)

    # CATEGORY: where the node appears in the Add Node menu.
    # Use "/" to create submenus. Example: "image/adjust" becomes Image > Adjust.
    CATEGORY = "example"

    # DESCRIPTION: tooltip text shown when hovering over the node in the search menu.
    # Supports plain text. Keep it concise (1-2 sentences).
    DESCRIPTION = "A template node that demonstrates all legacy v1 patterns."

    # RETURN_TYPES: tuple of ComfyUI type strings for each output socket.
    # Built-in types: "IMAGE", "MASK", "LATENT", "CONDITIONING", "MODEL",
    #   "CLIP", "VAE", "CONTROL_NET", "STRING", "INT", "FLOAT", "BOOLEAN"
    # You can also define custom types as arbitrary strings.
    RETURN_TYPES = ("IMAGE", "MASK", "FLOAT")

    # RETURN_NAMES: tuple of display names for each output socket.
    # Must match the length of RETURN_TYPES.
    RETURN_NAMES = ("image", "mask", "factor")

    # FUNCTION: name of the method ComfyUI will call to execute this node.
    # Almost always "execute".
    FUNCTION = "execute"

    # OUTPUT_NODE: set to True if this node produces final output (e.g., SaveImage,
    # PreviewImage). When True, the node can be a terminal node with no downstream.
    OUTPUT_NODE = False

    # INPUT_IS_LIST: set to True to receive all connected inputs as lists.
    # Useful for batch processing nodes that operate on multiple items.
    INPUT_IS_LIST = False

    # OUTPUT_IS_LIST: set to True if your execute() returns lists.
    # Each output will be wrapped as a list of items.
    OUTPUT_IS_LIST = False

    # SEARCH_ALIASES: alternative search terms so users can find this node
    # by typing different keywords in the search menu.
    SEARCH_ALIASES = ["template", "example", "demo node"]

    # -------------------------------------------------------------------------
    # Input definitions
    # -------------------------------------------------------------------------

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        """
        Define the input sockets for this node.

        Returns a dict with up to three keys:
          "required"  - inputs that MUST be connected (shown with solid dots)
          "optional"  - inputs that MAY be connected (shown with hollow dots)
          "hidden"    - inputs not shown in the UI but available to the function
                        (used for on-the-fly prompts, extra_pnginfo, unique_id, etc.)

        Each key maps to a dict of:
          input_name -> (type_str, config_dict)

        Config dict keys vary by type:
          For INT/FLOAT: "default", "min", "max", "step", "display" ("number"/"slider")
          For STRING:    "default", "multiline" (True/False), "dynamicPrompts" (True/False)
          For BOOLEAN:   "default"
          For COMBO:     list of allowed values (passed as a plain list, not a tuple)
          For IMAGE/MASK/etc: no config needed, pass an empty dict {}
        """
        return {
            "required": {
                # Image input — connected from any node that outputs IMAGE
                "image": ("IMAGE", {
                    # IMAGE inputs typically have no config options
                    # An IMAGE tensor has shape [B, H, W, C] with values in [0, 1]
                }),

                # Float input with slider display
                "strength": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.01,
                    "display": "slider",   # "number" for a text box, "slider" for a slider
                }),

                # Integer input with number display
                "iterations": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "display": "number",
                }),

                # Combo (dropdown) input
                "mode": (["fast", "quality", "balanced"], {
                    "default": "fast",
                }),

                # String input (multiline)
                "prompt": ("STRING", {
                    "default": "a beautiful landscape",
                    "multiline": True,
                    "dynamicPrompts": True,   # enables dynamic prompt widget
                }),
            },
            "optional": {
                # Optional mask input — node should handle the case where this is None
                "mask": ("MASK", {}),

                # Optional float with a default
                "bias": ("FLOAT", {
                    "default": 0.0,
                    "min": -1.0,
                    "max": 1.0,
                    "step": 0.01,
                }),
            },
            "hidden": {
                # unique_id: a unique identifier for this node instance
                # Useful for tracking node state or sending progress updates
                "unique_id": "UNIQUE_ID",

                # extra_pnginfo: workflow metadata passed when saving images
                "extra_pnginfo": "EXTRA_PNGINFO",

                # prompt: the full prompt dict for the current queue item
                "prompt": "PROMPT",
            },
        }

    # -------------------------------------------------------------------------
    # Input validation (optional)
    # -------------------------------------------------------------------------

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs) -> bool | str:
        """
        Validate inputs before execution. Called after the user connects
        wires but before execute() runs.

        Return True if inputs are valid.
        Return a string describing the error if invalid.
        Return False for a generic error message.

        This is optional — omit the method entirely if no validation is needed.
        """
        # Example: validate that strength is positive
        strength = kwargs.get("strength", 1.0)
        if isinstance(strength, (int, float)) and strength < 0:
            return "strength must be non-negative"

        # Example: validate combo value
        mode = kwargs.get("mode", "fast")
        if mode not in ("fast", "quality", "balanced"):
            return f"mode must be one of: fast, quality, balanced"

        return True

    # -------------------------------------------------------------------------
    # Change detection (optional)
    # -------------------------------------------------------------------------

    @classmethod
    def IS_CHANGED(cls, **kwargs) -> Any:
        """
        Called to determine if the node needs to re-execute.
        Return a value that changes when inputs change. ComfyUI compares
        the returned value to the previous one to decide whether to cache.

        Common patterns:
          - Return a hash of the inputs
          - Return a timestamp for nodes that always re-execute
          - Return the relevant input value directly

        This is optional — omit if the node should re-execute every time
        its direct inputs change (the default behavior).
        """
        import hashlib

        # Hash relevant inputs to detect changes
        m = hashlib.sha256()
        m.update(str(kwargs.get("strength", "")).encode())
        m.update(str(kwargs.get("iterations", "")).encode())
        m.update(str(kwargs.get("mode", "")).encode())
        m.update(str(kwargs.get("prompt", "")).encode())
        return m.hexdigest()

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def execute(
        self,
        image: torch.Tensor,
        strength: float,
        iterations: int,
        mode: str,
        prompt: str,
        mask: torch.Tensor | None = None,
        bias: float = 0.0,
        unique_id: str = "",
        extra_pnginfo: dict | None = None,
        prompt: dict | None = None,
    ) -> tuple:
        """
        Main execution method. Called when the node runs.

        Args:
            image: Input image tensor [B, H, W, C], values in [0, 1]
            strength: Float parameter controlling effect intensity
            iterations: Integer parameter for repeat count
            mode: String combo parameter
            prompt: String text input
            mask: Optional mask tensor [B, H, W], values in [0, 1]
            bias: Optional float parameter
            unique_id: Hidden input — this node instance's unique ID
            extra_pnginfo: Hidden input — workflow metadata
            prompt: Hidden input — full prompt dict

        Returns:
            A tuple matching RETURN_TYPES order: (image, mask, factor)
        """
        # --- Access image properties ---
        batch_size, height, width, channels = image.shape
        device = image.device

        # --- Apply the processing logic ---
        result = image.clone()

        # Example: apply strength scaling with iterations
        for _ in range(iterations):
            result = result * strength + bias

        # Example: clamp to valid range
        result = torch.clamp(result, 0.0, 1.0)

        # --- Handle optional mask ---
        if mask is not None:
            # Ensure mask shape matches image [B, H, W] -> [B, H, W, 1]
            if mask.dim() == 3:
                mask = mask.unsqueeze(-1)
            # Apply mask: keep result where mask is 1, keep original where mask is 0
            result = result * mask + image * (1 - mask)
        else:
            # Create a full mask if none provided
            mask = torch.ones(batch_size, height, width, device=device)

        # --- Compute a float output ---
        factor = strength * iterations

        # --- Return outputs as a tuple matching RETURN_TYPES ---
        return (result, mask.squeeze(-1), factor)


# =============================================================================
# Node Registration
# =============================================================================
# In your __init__.py, register this node:
#
#   from .legacy_node import MyLegacyNode
#   NODE_CLASS_MAPPINGS = {"MyLegacyNode": MyLegacyNode}
#   NODE_DISPLAY_NAME_MAPPINGS = {"MyLegacyNode": "My Legacy Node"}
#
# =============================================================================


# =============================================================================
# Quick Reference: Minimal Node
# =============================================================================
# class MinimalNode:
#     """The absolute minimum viable node."""
#     RETURN_TYPES = ("IMAGE",)
#     FUNCTION = "execute"
#     CATEGORY = "example"
#
#     @classmethod
#     def INPUT_TYPES(cls):
#         return {"required": {"image": ("IMAGE", {})}}
#
#     def execute(self, image):
#         return (image,)
