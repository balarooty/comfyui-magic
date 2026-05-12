#!/usr/bin/env bash
# ================================================================== #
#  ComfyUI-Magic — Model Downloader
#
#  Downloads all required models for LTX 2.3 chained scene generation.
#
#  Usage:
#    COMFYUI_DIR=/workspace/ComfyUI bash scripts/download_models.sh
#
#  Environment variables (all optional):
#    COMFYUI_DIR          ComfyUI root directory (default: /workspace/ComfyUI)
#    HF_TOKEN             Hugging Face auth token for gated models
#    ARIA2_CONNECTIONS    Parallel connections (default: 16)
#    ARIA2_SPLITS         Download splits (default: 16)
#    ARIA2_CHUNK_SIZE     Chunk size (default: 1M)
# ================================================================== #
set -euo pipefail

COMFYUI_DIR="${COMFYUI_DIR:-/workspace/runpod-slim/ComfyUI}"
BASE_DIR="${COMFYUI_DIR}/models"

ARIA2_CONNECTIONS="${ARIA2_CONNECTIONS:-16}"
ARIA2_SPLITS="${ARIA2_SPLITS:-16}"
ARIA2_CHUNK_SIZE="${ARIA2_CHUNK_SIZE:-1M}"

# ------------------------------------------------------------------ #
log() { echo "==> $*"; }
warn() { echo "WARNING: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

install_aria2() {
    if command -v aria2c >/dev/null 2>&1; then
        log "aria2 already installed ($(aria2c --version | head -1))"
        return
    fi

    log "aria2 not found, installing..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq
        sudo apt-get install -y aria2
    elif command -v apt >/dev/null 2>&1; then
        sudo apt update -qq
        sudo apt install -y aria2
    elif command -v brew >/dev/null 2>&1; then
        brew install aria2
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm aria2
    else
        die "Could not install aria2 automatically. Install aria2 and rerun."
    fi
}

download_file() {
    local target_dir="$1"
    local output_name="$2"
    local url="$3"
    local target_path="${target_dir}/${output_name}"

    mkdir -p "${target_dir}"

    if [ -s "${target_path}" ]; then
        local size
        size=$(du -h "${target_path}" 2>/dev/null | cut -f1)
        log "Skipping existing ${output_name} (${size})"
        return
    fi

    log "Downloading ${output_name}..."
    local args=(
        -x "${ARIA2_CONNECTIONS}"
        -s "${ARIA2_SPLITS}"
        -k "${ARIA2_CHUNK_SIZE}"
        --continue=true
        --auto-file-renaming=false
        --allow-overwrite=true
        --summary-interval=30
        -d "${target_dir}"
        -o "${output_name}"
    )

    if [ -n "${HF_TOKEN:-}" ]; then
        args+=(--header "Authorization: Bearer ${HF_TOKEN}")
    fi

    if ! aria2c "${args[@]}" "${url}"; then
        warn "Failed to download ${output_name} from ${url}"
        return 1
    fi

    local final_size
    final_size=$(du -h "${target_path}" 2>/dev/null | cut -f1)
    log "Downloaded ${output_name} (${final_size})"
}

# ------------------------------------------------------------------ #
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   🎬 ComfyUI-Magic Model Downloader     ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
log "ComfyUI dir:      ${COMFYUI_DIR}"
log "Models dir:       ${BASE_DIR}"
[ -n "${HF_TOKEN:-}" ] && log "HF auth:          token provided" || log "HF auth:          none (public repos only)"
echo ""

install_aria2

# ------------------------------------------------------------------ #
log "Creating model directories..."
mkdir -p \
    "${BASE_DIR}/checkpoints" \
    "${BASE_DIR}/loras" \
    "${BASE_DIR}/text_encoders" \
    "${BASE_DIR}/latent_upscale_models" \
    "${BASE_DIR}/vae" \
    "${BASE_DIR}/diffusion_models"

# ================================================================== #
echo ""
log "━━━ Downloading LTX 2.3 distilled generation stack ━━━"
echo ""

# Main diffusion model — 22B param, fp8 quantized
download_file \
    "${BASE_DIR}/checkpoints" \
    "ltx-2.3-22b-dev-fp8.safetensors" \
    "https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors"

# Distilled LoRA for 4-step fast inference (384 rank)
download_file \
    "${BASE_DIR}/loras" \
    "ltx-2.3-22b-distilled-lora-384.safetensors" \
    "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-distilled-lora-384.safetensors"

# Distilled checkpoint (alternative to base + LoRA)
download_file \
    "${BASE_DIR}/diffusion_models" \
    "ltx-2.3-22b-distilled-1.1.safetensors" \
    "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-distilled-1.1.safetensors"

# Gemma 3 12B text encoder (fp4 mixed — low VRAM)
download_file \
    "${BASE_DIR}/text_encoders" \
    "gemma_3_12B_it_fp4_mixed.safetensors" \
    "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors"

# Gemma abliterated LoRA (uncensored text encoder)
download_file \
    "${BASE_DIR}/loras" \
    "gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors" \
    "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors"

# LTX Video VAE
download_file \
    "${BASE_DIR}/vae" \
    "ltx_video_2_1_vae.safetensors" \
    "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx_video_2_1_vae.safetensors"

# Spatial upscaler 2× (optional but recommended)
download_file \
    "${BASE_DIR}/latent_upscale_models" \
    "ltx-2.3-spatial-upscaler-x2-1.1.safetensors" \
    "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.1.safetensors"

# ================================================================== #
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   🎬 Download Summary                    ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

count_models() {
    local dir="$1"
    if [ -d "${dir}" ]; then
        find "${dir}" -maxdepth 1 -name "*.safetensors" -type f 2>/dev/null | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

log "Models downloaded:"
log "  checkpoints:          $(count_models "${BASE_DIR}/checkpoints") files"
log "  diffusion_models:     $(count_models "${BASE_DIR}/diffusion_models") files"
log "  loras:                $(count_models "${BASE_DIR}/loras") files"
log "  text_encoders:        $(count_models "${BASE_DIR}/text_encoders") files"
log "  vae:                  $(count_models "${BASE_DIR}/vae") files"
log "  latent_upscale:       $(count_models "${BASE_DIR}/latent_upscale_models") files"

echo ""
log "All downloads completed."
log "Restart ComfyUI or click Refresh in the UI."
echo ""
