"""Real subject motion via fal.ai cloud image-to-video (Hailuo / Seedance / Kling).

Local Wan 2.1 only does slow camera moves; these cloud models animate actual
subject motion (people walking, hands working, animals, machinery) for a few
cents a clip. Feed the Qwen still + a motion prompt, get back a real video clip.

Setup (in your OWN terminal, never paste the key into chat):
  pip install fal-client            (already done in the project venv)
  export FAL_KEY=...                 (fal.ai -> dashboard -> Keys)
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

from . import config


def enabled() -> bool:
    return bool(os.environ.get("FAL_KEY"))


def still(prompt: str, dest: Path) -> Path | None:
    """Generate a realistic b-roll still via fal FLUX (no pod). None on failure."""
    if not enabled():
        return None
    try:
        import fal_client

        args = {"prompt": prompt}
        args.update(config.FAL_STILL_ARGS)
        result = fal_client.subscribe(config.FAL_STILL_MODEL, arguments=args, with_logs=False)
        imgs = (result or {}).get("images") or []
        url = imgs[0].get("url") if imgs else None
        if not url:
            return None
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest
    except Exception as e:
        print(f"       (fal still failed: {e})", flush=True)
        return None


def generate(image_path: Path, prompt: str, dest: Path) -> Path | None:
    """Animate `image_path` into a real-motion clip via fal.ai. None on failure."""
    if not enabled():
        return None
    try:
        import fal_client

        image_url = fal_client.upload_file(str(image_path))
        args = {"image_url": image_url, "prompt": f"{prompt}, {config.FAL_MOTION_CUE}"}
        args.update(config.FAL_MOTION_ARGS)          # model-specific (resolution, duration, ...)
        result = fal_client.subscribe(config.FAL_MOTION_MODEL, arguments=args, with_logs=False)
        url = (result or {}).get("video", {}).get("url")
        if not url:
            return None
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest
    except Exception as e:
        print(f"       (fal motion failed: {e})", flush=True)
        return None
