#!/bin/bash
# All-in-one setup for fresh ComfyUI RunPod pod (A40 48GB, 150GB volume)
# Installs everything needed for video quality test: CogVideoX-5B vs Wan 2.1
# Plus SD3.5 for generating source stills
set -e

# Auto-detect ComfyUI location
if [ -d "/workspace/ComfyUI" ]; then
  COMFY="/workspace/ComfyUI"
elif [ -d "/workspace/runpod-slim/ComfyUI" ]; then
  COMFY="/workspace/runpod-slim/ComfyUI"
else
  echo "ERROR: Cannot find ComfyUI. Please set COMFY= path manually."
  exit 1
fi
echo "Found ComfyUI at: $COMFY"
MODELS="$COMFY/models"
CUSTOM="$COMFY/custom_nodes"

echo "=========================================="
echo "  Pod Setup: Video Quality Test"
echo "=========================================="

# --- Custom Nodes ---
echo ""
echo ">>> Installing custom nodes..."
cd "$CUSTOM"

# CogVideoX wrapper
if [ ! -d "CogVideoXWrapper" ]; then
  git clone https://github.com/kijai/ComfyUI-CogVideoXWrapper.git CogVideoXWrapper
  pip install -r CogVideoXWrapper/requirements.txt 2>/dev/null || true
fi

# Wan video support
if [ ! -d "ComfyUI-WanVideoWrapper" ]; then
  git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git ComfyUI-WanVideoWrapper
  pip install -r ComfyUI-WanVideoWrapper/requirements.txt 2>/dev/null || true
fi

# VideoHelperSuite (VHS_VideoCombine for saving videos)
if [ ! -d "ComfyUI-VideoHelperSuite" ]; then
  git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git ComfyUI-VideoHelperSuite
  pip install -r ComfyUI-VideoHelperSuite/requirements.txt 2>/dev/null || true
fi

# KJNodes (image resize etc)
if [ ! -d "ComfyUI-KJNodes" ]; then
  git clone https://github.com/kijai/ComfyUI-KJNodes.git ComfyUI-KJNodes
  pip install -r ComfyUI-KJNodes/requirements.txt 2>/dev/null || true
fi

echo ">>> Custom nodes done."

# --- Text Encoders (shared) ---
echo ""
echo ">>> Downloading text encoders..."
cd "$MODELS/text_encoders"

# T5-XXL fp8 (used by SD3.5, CogVideoX, FLUX)
if [ ! -f "t5xxl_fp8_e4m3fn.safetensors" ]; then
  wget -q --show-progress -O t5xxl_fp8_e4m3fn.safetensors \
    "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors"
fi

# CLIP-L (used by SD3.5, FLUX)
if [ ! -f "clip_l.safetensors" ]; then
  wget -q --show-progress -O clip_l.safetensors \
    "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors"
fi

# CLIP-G (used by SD3.5)
if [ ! -f "clip_g.safetensors" ]; then
  wget -q --show-progress -O clip_g.safetensors \
    "https://huggingface.co/stabilityai/stable-diffusion-3.5-large/resolve/main/text_encoders/clip_g.safetensors"
fi

echo ">>> Text encoders done."

# --- SD3.5 Large (for source stills) ---
echo ""
echo ">>> Downloading SD3.5 Large checkpoint..."
cd "$MODELS/checkpoints"

if [ ! -f "sd3.5_large.safetensors" ]; then
  wget -q --show-progress -O sd3.5_large.safetensors \
    "https://huggingface.co/stabilityai/stable-diffusion-3.5-large/resolve/main/sd3.5_large.safetensors"
fi

echo ">>> SD3.5 done."

# --- CogVideoX-5B ---
# Model auto-downloads via DownloadAndLoadCogVideoModel node
# Just need the T5 encoder (already downloaded above)
echo ""
echo ">>> CogVideoX-5B: model will auto-download on first run via ComfyUI node."

# --- Wan 2.1 14B ---
echo ""
echo ">>> Downloading Wan 2.1 models..."

# Wan diffusion model (GGUF quantized to fit A40)
cd "$MODELS/diffusion_models"
if [ ! -f "wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors" ]; then
  wget -q --show-progress -O wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors \
    "https://huggingface.co/comfyanonymous/wan_2.1_comfyui/resolve/main/wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors"
fi

# Wan VAE
cd "$MODELS/vae"
if [ ! -f "wan_2.1_vae.safetensors" ]; then
  wget -q --show-progress -O wan_2.1_vae.safetensors \
    "https://huggingface.co/comfyanonymous/wan_2.1_comfyui/resolve/main/wan_2.1_vae.safetensors"
fi

# Wan CLIP vision
cd "$MODELS/clip_vision"
if [ ! -f "clip_vision_h.safetensors" ]; then
  wget -q --show-progress -O clip_vision_h.safetensors \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors"
fi

echo ">>> Wan 2.1 models done."

# --- Clone pipeline repo ---
echo ""
echo ">>> Cloning pipeline repo..."
cd /workspace
if [ ! -d "tennessee-bound" ]; then
  git clone https://github.com/samscoopes-sudo/tennessee-bound.git
  cd tennessee-bound
  git checkout claude/chat-session-1u0cdv
else
  cd tennessee-bound
  git pull origin claude/chat-session-1u0cdv 2>/dev/null || true
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Disk usage:"
du -sh $MODELS/checkpoints $MODELS/diffusion_models $MODELS/text_encoders $MODELS/vae $MODELS/clip_vision 2>/dev/null
echo ""
echo "Next steps:"
echo "  1. Restart ComfyUI if it was already running"
echo "  2. Run the test:"
echo "     cd /workspace/tennessee-bound/pipeline"
echo "     python3 test_models.py --comfy http://127.0.0.1:8188"
echo ""
