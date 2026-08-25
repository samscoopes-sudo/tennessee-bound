#!/usr/bin/env python3
"""One-shot runner for the Shelby test video.

Skips voice (vo.wav is already in the run folder) and runs the rest of the
pipeline directly: plan -> avatars -> align -> itemize -> motion -> render -> assemble.
Run it with:  .venv\\Scripts\\python.exe finish.py
"""
import subprocess
import sys
from pathlib import Path

PY = sys.executable
HERE = Path(__file__).resolve().parent

CH = "mychannel"
SLUG = "the-story-of-the-ford-shelby-mustang"
POD = "https://ueha1vfnef6ph3-8188.proxy.runpod.net"
RUN = f"channels/{CH}/runs/{SLUG}"
SCRIPT = f"{RUN}/script.txt"
SHOTS = f"{RUN}/shot-list.json"

# Test mode: only render the first few shots (fast + cheap). Set FULL=True for the
# whole 5-minute video (takes ~30-60 min of pod time).
FULL = True
LIMIT = [] if FULL else ["--limit", "6"]


def run(args):
    print("\n>>> " + " ".join(str(a) for a in args), flush=True)
    r = subprocess.run(args, cwd=str(HERE))
    if r.returncode != 0:
        print(f"\n!!! STEP FAILED (exit {r.returncode}) — copy the error above to Claude.")
        sys.exit(1)


if not (HERE / RUN / "vo.wav").exists():
    print(f"!!! No vo.wav found at {RUN}/vo.wav — put the narration there first.")
    sys.exit(1)

print(f"Using existing narration: {RUN}/vo.wav  (skipping voice)")

run([PY, "run.py", "plan", "--channel", CH, "--run", SLUG, "--script", SCRIPT])
run([PY, "inject_avatars.py", SHOTS])
run([PY, "run.py", "align", "--channel", CH, "--run", SLUG])
run([PY, "-c", f"from director import items, channels; c=channels.load('{CH}'); "
                f"items.itemize('{SHOTS}', scene_style=c.scene_style)"])
run([PY, "_reflag_motion.py", SHOTS, "4"])
run([PY, "run.py", "generate", "--channel", CH, "--run", SLUG, "--comfy", POD, "--only", "broll"] + LIMIT)
run([PY, "run.py", "generate", "--channel", CH, "--run", SLUG, "--comfy", POD, "--only", "avatar"] + LIMIT)
run([PY, "run.py", "assemble", "--channel", CH, "--run", SLUG])

print("\n=== DONE ===")
print(f"Your video: {RUN}/output/video.mp4")
