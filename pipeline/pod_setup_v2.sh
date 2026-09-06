#!/bin/bash
set -e
C="/workspace/runpod-slim/ComfyUI"
M="$C/models"
N="$C/custom_nodes"
cd "$N"
echo "=== Custom Nodes ==="
for r in kijai/ComfyUI-CogVideoXWrapper kijai/ComfyUI-WanVideoWrapper Kosinkadink/ComfyUI-VideoHelperSuite kijai/ComfyUI-KJNodes; do
d=$(basename $r)
[ -d "$d" ] || git clone "https://github.com/$r.git" "$d"
pip install -r "$d/requirements.txt" 2>/dev/null || true
done
echo "=== Text Encoders ==="
mkdir -p "$M/text_encoders"
cd "$M/text_encoders"
F="https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main"
S="https://huggingface.co/stabilityai/stable-diffusion-3.5-large/resolve/main"
[ -f t5xxl_fp8_e4m3fn.safetensors ] || wget -O t5xxl_fp8_e4m3fn.safetensors "$F/t5xxl_fp8_e4m3fn.safetensors"
[ -f clip_l.safetensors ] || wget -O clip_l.safetensors "$F/clip_l.safetensors"
[ -f clip_g.safetensors ] || wget -O clip_g.safetensors "$S/text_encoders/clip_g.safetensors"
echo "=== SD3.5 Large ==="
mkdir -p "$M/checkpoints"
cd "$M/checkpoints"
[ -f sd3.5_large.safetensors ] || wget -O sd3.5_large.safetensors "$S/sd3.5_large.safetensors"
echo "=== Wan 2.1 ==="
W="https://huggingface.co/comfyanonymous/wan_2.1_comfyui/resolve/main"
mkdir -p "$M/diffusion_models"
cd "$M/diffusion_models"
[ -f wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors ] || wget -O wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors "$W/wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors"
mkdir -p "$M/vae"
cd "$M/vae"
[ -f wan_2.1_vae.safetensors ] || wget -O wan_2.1_vae.safetensors "$W/wan_2.1_vae.safetensors"
mkdir -p "$M/clip_vision"
cd "$M/clip_vision"
[ -f clip_vision_h.safetensors ] || wget -O clip_vision_h.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors"
echo "=== Repo ==="
cd /workspace
[ -d tennessee-bound ] || git clone https://github.com/samscoopes-sudo/tennessee-bound.git
cd tennessee-bound && git checkout claude/chat-session-1u0cdv
echo "DONE"
