#!/usr/bin/env bash
# ================================================================== #
#  ComfyUI-Magic — Custom Node Installer
#
#  Clones or updates the comfyui-magic node pack into ComfyUI's
#  custom_nodes directory.
#
#  Usage:
#    COMFYUI_DIR=/workspace/ComfyUI bash scripts/install_custom_node.sh
#
#  Environment variables (all optional):
#    COMFYUI_DIR          ComfyUI root (default: /workspace/ComfyUI)
#    MAGIC_REPO_URL       Git clone URL (default: this repo)
#    PYTHON_BIN           Python to use (auto-detected)
# ================================================================== #
set -euo pipefail

COMFYUI_DIR="${COMFYUI_DIR:-/workspace/runpod-slim/ComfyUI}"
REPO_URL="${MAGIC_REPO_URL:-https://github.com/balarooty/comfyui-magic.git}"
NODE_DIR="${COMFYUI_DIR}/custom_nodes/comfyui-magic"

# ------------------------------------------------------------------ #
log() { echo "==> $*"; }
warn() { echo "WARNING: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   🎬 ComfyUI-Magic Node Installer        ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
log "ComfyUI dir: ${COMFYUI_DIR}"
log "Repo URL:    ${REPO_URL}"
log "Install dir: ${NODE_DIR}"
echo ""

# ------------------------------------------------------------------ #
if ! command -v git >/dev/null 2>&1; then
    die "git is required but was not found."
fi

# ------------------------------------------------------------------ #
mkdir -p "${COMFYUI_DIR}/custom_nodes"

if [ -d "${NODE_DIR}/.git" ]; then
    log "Existing install found. Updating..."
    git -C "${NODE_DIR}" fetch --all --prune
    git -C "${NODE_DIR}" pull --ff-only
    log "Updated to $(git -C "${NODE_DIR}" rev-parse --short HEAD)"
elif [ -e "${NODE_DIR}" ]; then
    die "${NODE_DIR} exists but is not a git checkout. Move it away or remove it, then rerun."
else
    log "Cloning comfyui-magic..."
    git clone "${REPO_URL}" "${NODE_DIR}"
    log "Cloned at $(git -C "${NODE_DIR}" rev-parse --short HEAD)"
fi

# ------------------------------------------------------------------ #
# Also install ComfyUI-LTXVideo dependency if not present
LTXV_DIR="${COMFYUI_DIR}/custom_nodes/ComfyUI-LTXVideo"
if [ ! -d "${LTXV_DIR}" ]; then
    log "ComfyUI-LTXVideo not found — installing dependency..."
    git clone "https://github.com/Lightricks/ComfyUI-LTXVideo.git" "${LTXV_DIR}"
    log "Installed ComfyUI-LTXVideo at $(git -C "${LTXV_DIR}" rev-parse --short HEAD)"
else
    log "ComfyUI-LTXVideo already installed."
fi

# Also install VideoHelperSuite for VHS_VideoCombine
VHS_DIR="${COMFYUI_DIR}/custom_nodes/ComfyUI-VideoHelperSuite"
if [ ! -d "${VHS_DIR}" ]; then
    log "VideoHelperSuite not found — installing dependency..."
    git clone "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" "${VHS_DIR}"
    log "Installed VideoHelperSuite at $(git -C "${VHS_DIR}" rev-parse --short HEAD)"
else
    log "VideoHelperSuite already installed."
fi

# ------------------------------------------------------------------ #
echo ""
log "━━━ Installed Node Pack Contents ━━━"
log "  Custom Nodes:  3 (FW_LTXPipeMake, FW_LTXScene, FW_VideoBatcher)"
log "  Workflows:     1 (ltx23_chained_scenes.json)"
echo ""

# Count node files for verification
if [ -d "${NODE_DIR}/nodes" ]; then
    NODE_FILES=$(find "${NODE_DIR}/nodes" -name "*.py" ! -name "__init__.py" | wc -l | tr -d ' ')
    log "  Python node files found: ${NODE_FILES}"
fi

# Count dependencies
DEP_COUNT=0
[ -d "${LTXV_DIR}" ] && DEP_COUNT=$((DEP_COUNT + 1))
[ -d "${VHS_DIR}" ] && DEP_COUNT=$((DEP_COUNT + 1))
log "  Dependencies installed: ${DEP_COUNT}/2"

echo ""
log "ComfyUI-Magic custom node installed successfully."
log "Restart ComfyUI or click Refresh in the UI."
echo ""
