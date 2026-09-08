#!/bin/bash
set -e
C="/workspace/runpod-slim/ComfyUI"
M="$C/models"
N="$C/custom_nodes"
cd "$N"
echo "=== Custom Nodes ==="
for r in kijai/ComfyUI-WanVideoWrapper Kosinkadink/ComfyUI-VideoHelperSuite kijai/ComfyUI-KJNodes niknah/ComfyUI-F5-TTS; do
d=$(basename $r)
[ -d "$d" ] || git clone "https://github.com/$r.git" "$d"
pip install -r "$d/requirements.txt" 2>/dev/null || true
done
echo "=== Text Encoders ==="
mkdir -p "$M/text_encoders"
cd "$M/text_encoders"
W="https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files"
[ -f umt5_xxl_fp16.safetensors ] || wget -O umt5_xxl_fp16.safetensors "$W/text_encoders/umt5_xxl_fp16.safetensors"
echo "=== Wan 2.1 1.3B ==="
mkdir -p "$M/diffusion_models"
cd "$M/diffusion_models"
[ -f wan2.1_t2v_1.3B_bf16.safetensors ] || wget -O wan2.1_t2v_1.3B_bf16.safetensors "$W/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors"
mkdir -p "$M/vae"
cd "$M/vae"
[ -f wan_2.1_vae.safetensors ] || wget -O wan_2.1_vae.safetensors "$W/vae/wan_2.1_vae.safetensors"
mkdir -p "$M/clip_vision"
cd "$M/clip_vision"
[ -f clip_vision_h.safetensors ] || wget -O clip_vision_h.safetensors "$W/clip_vision/clip_vision_h.safetensors"
echo "=== Repo ==="
cd /workspace
[ -d tennessee-bound ] || git clone https://github.com/samscoopes-sudo/tennessee-bound.git
cd tennessee-bound && git checkout claude/chat-session-1u0cdv
echo "DONE"
