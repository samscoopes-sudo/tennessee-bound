#!/bin/bash
# Run on the pod ONCE to download all test models + custom nodes.
# Usage:  bash test_models_setup.sh
set -e
cd /workspace/ComfyUI

echo "=== 1. SD3.5 Large (image model) ==="
# SD3.5 Large checkpoint — needs HuggingFace token with SD3.5 access
# Accept license at https://huggingface.co/stabilityai/stable-diffusion-3.5-large
if [ ! -f models/checkpoints/sd3.5_large.safetensors ]; then
  echo "Downloading SD3.5 Large..."
  wget -q --show-progress -O models/checkpoints/sd3.5_large.safetensors \
    "https://huggingface.co/stabilityai/stable-diffusion-3.5-large/resolve/main/sd3.5_large.safetensors"
else
  echo "SD3.5 Large already downloaded"
fi

# SD3.5 needs the same CLIP files FLUX uses (clip_l + t5xxl) — should already exist
# Plus clip_g for the triple CLIP:
if [ ! -f models/clip/clip_g.safetensors ]; then
  echo "Downloading CLIP-G for SD3.5..."
  wget -q --show-progress -O models/clip/clip_g.safetensors \
    "https://huggingface.co/stabilityai/stable-diffusion-3.5-large/resolve/main/text_encoders/clip_g.safetensors"
fi

echo ""
echo "=== 2. CogVideoX-5B (video model) ==="
# Custom node
if [ ! -d custom_nodes/ComfyUI-CogVideoXWrapper ]; then
  echo "Cloning CogVideoX wrapper..."
  cd custom_nodes
  git clone https://github.com/kijai/ComfyUI-CogVideoXWrapper.git
  cd ComfyUI-CogVideoXWrapper && pip install -r requirements.txt 2>/dev/null; cd ../..
else
  echo "CogVideoX wrapper already installed"
fi

# Model — downloads automatically on first use via the wrapper node,
# but we can pre-download for speed:
mkdir -p models/CogVideo
if [ ! -f models/CogVideo/cogvideox_5b_fun_fp8_e4m3fn.safetensors ]; then
  echo "Downloading CogVideoX-5B (fp8 quantized)..."
  wget -q --show-progress -O models/CogVideo/cogvideox_5b_fun_fp8_e4m3fn.safetensors \
    "https://huggingface.co/Kijai/CogVideoX_5b_fun_comfy/resolve/main/cogvideox_5b_fun_fp8_e4m3fn.safetensors"
else
  echo "CogVideoX-5B already downloaded"
fi

echo ""
echo "=== 3. HunyuanVideo (video model) ==="
if [ ! -d custom_nodes/ComfyUI-HunyuanVideoWrapper ]; then
  echo "Cloning HunyuanVideo wrapper..."
  cd custom_nodes
  git clone https://github.com/kijai/ComfyUI-HunyuanVideoWrapper.git
  cd ComfyUI-HunyuanVideoWrapper && pip install -r requirements.txt 2>/dev/null; cd ../..
else
  echo "HunyuanVideo wrapper already installed"
fi

echo ""
echo "=== Done ==="
echo "Restart ComfyUI to load new nodes:"
echo "  pkill -f 'python3 main.py' ; cd /workspace/ComfyUI && python3 main.py --listen 0.0.0.0 --port 8188 &"
echo ""
echo "Then run:  python3 test_models.py --comfy http://127.0.0.1:8188"
