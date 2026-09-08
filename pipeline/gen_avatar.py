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

AVATAR_IMAGE_URL = "https://files.genaipro.io/image_eff5539a-a268-4900-9c9a-5799cf5c3337_0.png"

TALKING_HEAD_SHOTS = [
    {
        "prompt": "The man in the image facing the camera, speaking calmly as a presenter, subtle lip movement and natural blinking, warm indoor lighting",
        "duration": 5,
        "name": "avatar_intro",
    },
    {
        "prompt": "The man in the image looking directly at camera, nodding slightly while speaking, friendly expression, natural gestures",
        "duration": 5,
        "name": "avatar_mid1",
    },
    {
        "prompt": "The man in the image speaking to camera with enthusiasm, slight hand gesture, warm smile, natural presenter energy",
        "duration": 5,
        "name": "avatar_mid2",
    },
    {
        "prompt": "The man in the image facing camera, speaking thoughtfully, calm closing statement expression, warm lighting",
        "duration": 5,
        "name": "avatar_outro",
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--image-only", action="store_true",
                    help="Only generate the avatar image")
    ap.add_argument("--image-url", default=AVATAR_IMAGE_URL,
                    help="GenAI Pro hosted URL of avatar image")
    args = ap.parse_args()

    veo = Veo(args.api_key)
    credits = veo.credits()
    print(f"Credits available: {credits}")

    if args.image_only:
        avatar_img = OUT / "avatar_presenter.png"
        if avatar_img.exists():
            print(f"Avatar image already exists: {avatar_img}")
        else:
            print("Generating avatar image...")
            veo.create_image(AVATAR_PROMPT, avatar_img)
            print(f"Avatar image saved: {avatar_img}")
        return

    # Generate talking head clips from the avatar image
    print(f"\nGenerating {len(TALKING_HEAD_SHOTS)} talking head clips...")
    print(f"Using avatar image: {args.image_url}\n")

    for shot in TALKING_HEAD_SHOTS:
        dest = OUT / f"{shot['name']}.mp4"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  [{shot['name']}] skip (cached)")
            continue
        print(f"  [{shot['name']}] {shot['prompt'][:60]}...")
        try:
            veo.frames_to_video(args.image_url, shot["prompt"], dest,
                                duration=shot["duration"])
            print(f"  [{shot['name']}] OK")
        except Exception as e:
            print(f"  [{shot['name']}] FAILED: {e}")


if __name__ == "__main__":
    main()
