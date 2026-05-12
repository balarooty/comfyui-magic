#!/usr/bin/env bash
# ================================================================== #
#  ComfyUI-Magic — Complete Setup
#
#  One-command installation: custom nodes + dependencies + all models.
#
#  Usage:
#    # Standard setup
#    COMFYUI_DIR=/workspace/ComfyUI bash scripts/setup_magic.sh
#
#    # With HF auth for gated models
#    HF_TOKEN=hf_xxxxx COMFYUI_DIR=/workspace/ComfyUI bash scripts/setup_magic.sh
#
#  Environment variables (all optional):
#    COMFYUI_DIR          ComfyUI root directory (default: /workspace/ComfyUI)
#    HF_TOKEN             Hugging Face auth token for gated models
# ================================================================== #
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   🎬 ComfyUI-Magic Complete Setup            ║"
echo "  ╠══════════════════════════════════════════════╣"
echo "  ║   Step 1: Install custom node + dependencies ║"
echo "  ║   Step 2: Download LTX 2.3 models            ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# Step 1: Install custom node pack + dependency packs
"${SCRIPT_DIR}/install_custom_node.sh"

# Step 2: Download all models
"${SCRIPT_DIR}/download_models.sh"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   🎬 ComfyUI-Magic setup complete!           ║"
echo "  ║                                               ║"
echo "  ║   Restart ComfyUI to load the new nodes.      ║"
echo "  ║   Load the workflow from:                      ║"
echo "  ║   example_workflows/ltx23_chained_scenes.json  ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
