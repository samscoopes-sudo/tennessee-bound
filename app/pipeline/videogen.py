"""AI video-generation adapter (tier 4 - deliberate last resort).

Only reached when stock and image gen can't cover a cue, and only within the
per-render second budget (config.MAX_AI_VIDEO_SECONDS). Point at a cheap video
model (Kling / Hailuo / Luma, etc.). Write an mp4 to `dest`, return True.
"""
from __future__ import annotations

from pathlib import Path

from .. import config


def generate_clip(prompt: str, seconds: float, dest: Path) -> bool:
    if not config.AI_VIDEO_GEN_API_KEY:
        return False
    # TODO: wire your video API here (submit -> poll -> download to dest).
    return False
