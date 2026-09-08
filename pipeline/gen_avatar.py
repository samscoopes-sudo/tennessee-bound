#!/usr/bin/env python3
"""Generate avatar presenter image and talking head clips via GenAI Pro."""
import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from director.veo import Veo

OUT = Path("atlanta_output")
OUT.mkdir(exist_ok=True)

AVATAR_PROMPT = (
    "Portrait photograph of a southern white American male in his mid 30s "
    "with short brown hair and light stubble, wearing a casual flannel shirt, "
    "facing directly toward the camera, friendly warm expression, "
    "natural window lighting, clean neutral background, "
    "chest and shoulders framing"
)

AVATAR_IMAGE = OUT / "avatar_presenter.png"

TALKING_HEAD_SHOTS = [
    {
        "prompt": "The man in the image standing in front of a bookshelf, greeting the viewer with a small wave, warm smile, soft indoor lighting from the left side",
        "duration": 8,
        "name": "avatar_intro",
    },
    {
        "prompt": "The man in the image walking slowly through a park outdoors, talking to the camera, trees and greenery in the background, natural sunlight, slight breeze",
        "duration": 8,
        "name": "avatar_mid1",
    },
    {
        "prompt": "The man in the image sitting at a desk leaning forward, gesturing with his hands while explaining something, laptop visible, overhead warm lamp light",
        "duration": 8,
        "name": "avatar_mid2",
    },
    {
        "prompt": "The man in the image standing on a rooftop at golden hour, city skyline behind him, wind in his hair, looking at camera with a thoughtful closing expression",
        "duration": 8,
        "name": "avatar_outro",
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--image-only", action="store_true",
                    help="Only generate the avatar image")
    args = ap.parse_args()

    veo = Veo(args.api_key)
    credits = veo.credits()
    print(f"Credits available: {credits}")

    if args.image_only:
        if AVATAR_IMAGE.exists():
            print(f"Avatar image already exists: {AVATAR_IMAGE}")
        else:
            print("Generating avatar image...")
            veo.create_image(AVATAR_PROMPT, AVATAR_IMAGE)
            print(f"Avatar image saved: {AVATAR_IMAGE}")
        return

    if not AVATAR_IMAGE.exists():
        print(f"ERROR: Avatar image not found at {AVATAR_IMAGE}")
        print("Run with --image-only first to generate it.")
        return

    print(f"\nGenerating {len(TALKING_HEAD_SHOTS)} talking head clips...")
    print(f"Using avatar image: {AVATAR_IMAGE}\n")

    for shot in TALKING_HEAD_SHOTS:
        dest = OUT / f"{shot['name']}.mp4"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  [{shot['name']}] skip (cached)")
            continue
        print(f"  [{shot['name']}] {shot['prompt'][:60]}...")
        try:
            veo.frames_to_video(str(AVATAR_IMAGE), shot["prompt"], dest,
                                duration=shot["duration"])
            print(f"  [{shot['name']}] OK")
        except Exception as e:
            print(f"  [{shot['name']}] FAILED: {e}")


if __name__ == "__main__":
    main()
