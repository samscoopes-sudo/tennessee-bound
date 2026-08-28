#!/usr/bin/env python3
"""Generate one avatar clip at steps 4, 5, and 6 for quality comparison."""
import subprocess
from pathlib import Path
from director.comfy import Comfy
from director import config

COMFY_URL = "http://127.0.0.1:8188"
AVATAR = Path("channels/dave/avatar.png")
VO = Path("channels/dave/runs/lawn-care-fall/vo.wav")
OUT = Path("channels/dave/runs/lawn-care-fall/output")
OUT.mkdir(parents=True, exist_ok=True)

# Slice 4s of audio from the first talking head shot (start=28s)
wav = OUT / "test_steps.wav"
subprocess.run(["ffmpeg", "-y", "-ss", "28", "-t", "4", "-i", str(VO),
                "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

comfy = Comfy(COMFY_URL)
frames = max(config.FPS, int(round(4.0 * config.FPS)))  # 4 seconds

for steps in [4, 5, 6]:
    dest = OUT / f"test_steps_{steps}.mp4"
    print(f"Generating {steps} steps -> {dest.name} ...", flush=True)
    try:
        comfy.infinitetalk(AVATAR, wav,
                           config.TALKING_HEAD_PROMPT, config.TALKING_HEAD_NEGATIVE,
                           config.VIDEO_W, config.VIDEO_H, frames, dest, steps=steps)
        print(f"  Done: {dest}", flush=True)
    except Exception as e:
        print(f"  FAILED: {e}", flush=True)

print("\nCompare: test_steps_4.mp4, test_steps_5.mp4, test_steps_6.mp4")
