#!/usr/bin/env python3
"""Generate avatar presenter image and sample talking head clips via GenAI Pro."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--image-only", action="store_true",
                    help="Only generate the avatar image, skip video samples")
    args = ap.parse_args()

    veo = Veo(args.api_key)
    credits = veo.credits()
    print(f"Credits available: {credits}")

    # Step 1: Generate avatar image
    avatar_img = OUT / "avatar_presenter.png"
    if avatar_img.exists():
        print(f"Avatar image already exists: {avatar_img}")
    else:
        print("Generating avatar image...")
        veo.create_image(AVATAR_PROMPT, avatar_img)
        print(f"Avatar image saved: {avatar_img}")

    if args.image_only:
        return

    # Step 2: Generate sample talking head clips from the image
    # The image URL needs to be the GenAI Pro hosted URL from the task result
    # For now, just generate text-to-video samples
    print("\nTo generate talking head clips from this image:")
    print("1. Upload the avatar image to GenAI Pro")
    print("2. Use frames-to-video with the image URL")
    print("(or run this script without --image-only after the image is hosted)")


if __name__ == "__main__":
    main()
