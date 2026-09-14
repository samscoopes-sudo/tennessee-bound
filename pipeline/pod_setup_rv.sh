#!/bin/bash
# RV Pipeline pod setup — installs ComfyUI + models for rv_sample.py
# Targets: NVIDIA L4 (24GB) or RTX 4090 (24GB)
# Usage: bash pod_setup_rv.sh

set -e
cd /workspace

COMFY=/workspace/ComfyUI
MODELS=$COMFY/models

# --- Install ComfyUI ---
if [ ! -d "$COMFY" ]; then
    echo "=== Installing ComfyUI ==="
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd $COMFY
    pip install -r requirements.txt
    cd /workspace
else
    echo "=== ComfyUI already installed ==="
fi

# --- Custom Nodes ---
echo "=== Installing custom nodes ==="
cd $COMFY/custom_nodes

# WanVideoWrapper (for InfiniteTalk + Wan I2V)
if [ ! -d "ComfyUI-WanVideoWrapper" ]; then
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git
    pip install -r ComfyUI-WanVideoWrapper/requirements.txt 2>/dev/null || true
fi

# KJNodes (utility nodes)
if [ ! -d "ComfyUI-KJNodes" ]; then
    git clone https://github.com/kijai/ComfyUI-KJNodes.git
    pip install -r ComfyUI-KJNodes/requirements.txt 2>/dev/null || true
fi

# VideoHelperSuite (video output)
if [ ! -d "ComfyUI-VideoHelperSuite" ]; then
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    pip install -r ComfyUI-VideoHelperSuite/requirements.txt 2>/dev/null || true
fi

cd /workspace

# --- Create model directories ---
mkdir -p $MODELS/diffusion_models/InfiniteTalk
mkdir -p $MODELS/text_encoders
mkdir -p $MODELS/vae
mkdir -p $MODELS/clip_vision
mkdir -p $MODELS/loras
mkdir -p $MODELS/checkpoints

# --- Download models ---
echo ""
echo "=== Downloading Flux models (for AI image generation) ==="

# Flux fp8 (~12GB)
if [ ! -f "$MODELS/diffusion_models/flux1-dev-fp8.safetensors" ]; then
    echo "Downloading flux1-dev-fp8.safetensors..."
    wget -q --show-progress -O $MODELS/diffusion_models/flux1-dev-fp8.safetensors \
        "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"
else
    echo "flux1-dev-fp8 already exists"
fi

# CLIP-L text encoder (~250MB)
if [ ! -f "$MODELS/text_encoders/clip_l.safetensors" ]; then
    echo "Downloading clip_l.safetensors..."
    wget -q --show-progress -O $MODELS/text_encoders/clip_l.safetensors \
        "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors"
else
    echo "clip_l already exists"
fi

# T5-XXL fp8 text encoder (~5GB)
if [ ! -f "$MODELS/text_encoders/t5xxl_fp8_e4m3fn.safetensors" ]; then
    echo "Downloading t5xxl_fp8_e4m3fn.safetensors..."
    wget -q --show-progress -O $MODELS/text_encoders/t5xxl_fp8_e4m3fn.safetensors \
        "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors"
else
    echo "t5xxl_fp8 already exists"
fi

# FLUX VAE (~300MB)
if [ ! -f "$MODELS/vae/ae.safetensors" ]; then
    echo "Downloading ae.safetensors (FLUX VAE)..."
    wget -q --show-progress -O $MODELS/vae/ae.safetensors \
        "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors"
else
    echo "FLUX VAE already exists"
fi

echo ""
echo "=== Downloading InfiniteTalk models (for avatar lip-sync) ==="

# InfiniteTalk GGUF Q4 (~8GB, lighter for L4)
if [ ! -f "$MODELS/diffusion_models/InfiniteTalk/Wan2_1-InfiniteTalk_Single_Q8.gguf" ]; then
    echo "Downloading InfiniteTalk Q8 model..."
    wget -q --show-progress -O $MODELS/diffusion_models/InfiniteTalk/Wan2_1-InfiniteTalk_Single_Q8.gguf \
        "https://huggingface.co/kijai/WanVideo_comfy/resolve/main/InfiniteTalk/Wan2_1-InfiniteTalk_Single_Q8.gguf"
else
    echo "InfiniteTalk Q8 already exists"
fi

# Wan 2.1 I2V 14B Q4 GGUF (~8GB)
if [ ! -f "$MODELS/diffusion_models/wan2.1-i2v-14b-480p-Q4_K_M.gguf" ]; then
    echo "Downloading wan2.1-i2v-14b Q4 GGUF..."
    wget -q --show-progress -O $MODELS/diffusion_models/wan2.1-i2v-14b-480p-Q4_K_M.gguf \
        "https://huggingface.co/kijai/WanVideo_comfy/resolve/main/wan2.1-i2v-14b-480p-Q4_K_M.gguf"
else
    echo "wan2.1-i2v Q4 already exists"
fi

# Wan 2.1 VAE bf16
if [ ! -f "$MODELS/vae/Wan2_1_VAE_bf16.safetensors" ]; then
    echo "Downloading Wan2_1_VAE_bf16..."
    wget -q --show-progress -O $MODELS/vae/Wan2_1_VAE_bf16.safetensors \
        "https://huggingface.co/kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors"
else
    echo "Wan VAE bf16 already exists"
fi

# UMT5-XXL fp8 text encoder for Wan
if [ ! -f "$MODELS/text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors" ]; then
    echo "Downloading umt5-xxl-enc-fp8..."
    wget -q --show-progress -O $MODELS/text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors \
        "https://huggingface.co/kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors"
else
    echo "umt5-xxl fp8 already exists"
fi

# CLIP Vision H
if [ ! -f "$MODELS/clip_vision/clip_vision_h.safetensors" ]; then
    echo "Downloading clip_vision_h..."
    wget -q --show-progress -O $MODELS/clip_vision/clip_vision_h.safetensors \
        "https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors"
else
    echo "clip_vision_h already exists"
fi

# LightX2V LoRA (speed LoRA for inference)
if [ ! -f "$MODELS/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors" ]; then
    echo "Downloading LightX2V LoRA..."
    wget -q --show-progress -O $MODELS/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors \
        "https://huggingface.co/kijai/WanVideo_comfy/resolve/main/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
else
    echo "LightX2V LoRA already exists"
fi

echo ""
echo "=== Summary ==="
echo "Models downloaded:"
du -sh $MODELS/diffusion_models/ $MODELS/text_encoders/ $MODELS/vae/ $MODELS/clip_vision/ $MODELS/loras/ 2>/dev/null
echo ""
echo "Total model size:"
du -sh $MODELS/
echo ""
echo "=== Setup complete ==="
echo "Start ComfyUI with: cd $COMFY && python main.py --listen 0.0.0.0 --port 8188"
