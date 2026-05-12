# =============================================================================
# ComfyUI Custom Node __init__.py Registration Templates
# =============================================================================
# This file controls how ComfyUI discovers and loads your custom nodes.
# Choose ONE of the patterns below and remove the others.
#
# Required exports:
#   NODE_CLASS_MAPPINGS      - dict mapping node ID -> node class
#   NODE_DISPLAY_NAME_MAPPINGS - dict mapping node ID -> display name
#   WEB_DIRECTORY (optional) - path to web extensions (JS/CSS)
# =============================================================================

import os

WEB_DIRECTORY = "./web"

# =============================================================================
# Pattern 1: Simple Registration
# =============================================================================
# Best for: Small nodes with 1-3 node classes. Direct and easy to read.
#
# Each node class is imported individually and added to the mappings dict.
# The key (e.g. "MyNode") is the internal ID used in workflows.
# The display name is what users see in the ComfyUI node search menu.

# from .nodes import MyNode, MyOtherNode
#
# NODE_CLASS_MAPPINGS = {
#     "MyNode": MyNode,
#     "MyOtherNode": MyOtherNode,
# }
#
# NODE_DISPLAY_NAME_MAPPINGS = {
#     "MyNode": "My Node",
#     "MyOtherNode": "My Other Node",
# }
#
# __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]


# =============================================================================
# Pattern 2: NODE_CONFIG Dict Pattern (KJNodes Style)
# =============================================================================
# Best for: Medium/large node packs with many classes. Keeps config DRY and
# centralized. Easy to add new nodes without touching the mapping logic.
#
# All node metadata lives in NODE_CONFIG. The generate_node_mappings()
# function builds the required dicts automatically.

# from .nodes import MyNode, MyOtherNode, AnotherNode
#
# NODE_CONFIG = {
#     "MyNode": {
#         "class": MyNode,
#         "name": "My Node",                    # optional, defaults to class.__name__
#     },
#     "MyOtherNode": {
#         "class": MyOtherNode,
#         "name": "My Other Node",
#     },
#     "AnotherNode": {
#         "class": AnotherNode,
#         "name": "Another Node",
#     },
# }
#
# def generate_node_mappings(config):
#     """Build NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS from a config dict."""
#     class_map = {}
#     name_map = {}
#     for key, val in config.items():
#         class_map[key] = val["class"]
#         name_map[key] = val.get("name", val["class"].__name__)
#     return class_map, name_map
#
# NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS = generate_node_mappings(NODE_CONFIG)
#
# __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]


# =============================================================================
# Pattern 3: Try/Except Isolation Pattern
# =============================================================================
# Best for: Node packs with optional dependencies or independent features.
# If one node fails to import (missing library, syntax error, etc.), the
# rest of the pack still loads. Errors are collected and logged.
#
# This is the most robust pattern for production node packs.

# from .nodes import BaseNode  # always-available base imports
#
# NODE_CLASS_MAPPINGS = {
#     "BaseNode": BaseNode,
# }
# NODE_DISPLAY_NAME_MAPPINGS = {
#     "BaseNode": "Base Node",
# }
#
# _IMPORT_ERRORS = []
#
# try:
#     from .nodes.feature_a import FeatureANode
#     NODE_CLASS_MAPPINGS["FeatureANode"] = FeatureANode
#     NODE_DISPLAY_NAME_MAPPINGS["FeatureANode"] = "Feature A Node"
# except Exception as e:
#     _IMPORT_ERRORS.append(("FeatureANode", str(e)))
#
# try:
#     from .nodes.feature_b import FeatureBNode
#     NODE_CLASS_MAPPINGS["FeatureBNode"] = FeatureBNode
#     NODE_DISPLAY_NAME_MAPPINGS["FeatureBNode"] = "Feature B Node"
# except Exception as e:
#     _IMPORT_ERRORS.append(("FeatureBNode", str(e)))
#
# try:
#     from .nodes.feature_c import FeatureCNode
#     NODE_CLASS_MAPPINGS["FeatureCNode"] = FeatureCNode
#     NODE_DISPLAY_NAME_MAPPINGS["FeatureCNode"] = "Feature C Node"
# except Exception as e:
#     _IMPORT_ERRORS.append(("FeatureCNode", str(e)))
#
# # Log any import failures so users can diagnose issues
# if _IMPORT_ERRORS:
#     import logging
#     logger = logging.getLogger(__name__)
#     for node_name, error in _IMPORT_ERRORS:
#         logger.warning(f"[comfyui-mypack] Failed to load {node_name}: {error}")
#
# __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]


# =============================================================================
# Pattern 4: Combined — Try/Except + NODE_CONFIG
# =============================================================================
# Best for: Large node packs that want both robustness and DRY config.

# from .nodes import BaseNode
#
# NODE_CLASS_MAPPINGS = {}
# NODE_DISPLAY_NAME_MAPPINGS = {}
# _IMPORT_ERRORS = []
#
# # Always-available nodes
# NODE_CLASS_MAPPINGS["BaseNode"] = BaseNode
# NODE_DISPLAY_NAME_MAPPINGS["BaseNode"] = "Base Node"
#
# # Optional feature nodes with isolated imports
# _OPTIONAL_NODES = [
#     ("FeatureANode", ".nodes.feature_a", "Feature A Node"),
#     ("FeatureBNode", ".nodes.feature_b", "Feature B Node"),
# ]
#
# for node_id, module_path, display_name in _OPTIONAL_NODES:
#     try:
#         import importlib
#         mod = importlib.import_module(module_path, package=__name__)
#         node_cls = getattr(mod, node_id)
#         NODE_CLASS_MAPPINGS[node_id] = node_cls
#         NODE_DISPLAY_NAME_MAPPINGS[node_id] = display_name
#     except Exception as e:
#         _IMPORT_ERRORS.append((node_id, str(e)))
#
# if _IMPORT_ERRORS:
#     import logging
#     logger = logging.getLogger(__name__)
#     for node_name, error in _IMPORT_ERRORS:
#         logger.warning(f"[comfyui-mypack] Failed to load {node_name}: {error}")
#
# __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
