#!/usr/bin/env python3
"""Generate avatar clips at steps 6-12 at native 832x480 to compare quality."""
import subprocess
from pathlib import Path
from director.comfy import Comfy

COMFY_URL = "http://127.0.0.1:8188"
AVATAR = Path("channels/dave/avatar.png")
VO = Path("channels/dave/runs/lawn-care-fall/vo.wav")
OUT = Path("channels/dave/runs/lawn-care-fall/output")
OUT.mkdir(parents=True, exist_ok=True)

wav = OUT / "test_steps.wav"
if not wav.exists():
    subprocess.run(["ffmpeg", "-y", "-ss", "28", "-t", "4", "-i", str(VO),
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

comfy = Comfy(COMFY_URL)
W, H = 832, 480
frames = int(round(4.0 * 25))  # 4 seconds at 25 fps

for steps in range(6, 13):
    dest = OUT / f"test_832_{steps}s.mp4"
    print(f"Generating {steps} steps @ {W}x{H} -> {dest.name} ...", flush=True)
    try:
        comfy.infinitetalk(AVATAR, wav,
                           "a bearded farmer speaking calmly to the camera, natural head movement, documentary interview, soft daylight",
                           "bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards",
                           W, H, frames, dest, steps=steps)
        print(f"  Done: {dest}", flush=True)
    except Exception as e:
        print(f"  FAILED: {e}", flush=True)

print(f"\nCompare: test_832_6s.mp4 through test_832_12s.mp4")
