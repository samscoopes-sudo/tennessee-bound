"""Runtime configuration, read from environment variables.

Nothing here is required to import the app; missing keys only disable the
feature that needs them (e.g. no STORYBLOCKS key -> that asset source is
skipped in the fallback ladder).
"""
from __future__ import annotations

import os
from pathlib import Path

# --- paths ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
STYLE_PRESET_DIR = BASE_DIR / "style-presets"
WORK_DIR = Path(os.getenv("WORK_DIR", "/tmp/video-agent"))
WORK_DIR.mkdir(parents=True, exist_ok=True)

# --- the director LLM (Claude) ------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DIRECTOR_MODEL = os.getenv("DIRECTOR_MODEL", "claude-sonnet-5")

# --- transcription ------------------------------------------------------
# tiny/base/small/medium/large-v3 - base is a good free default on CPU.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# --- asset sources (cheapest first) -------------------------------------
STORYBLOCKS_PUBLIC_KEY = os.getenv("STORYBLOCKS_PUBLIC_KEY", "")
STORYBLOCKS_PRIVATE_KEY = os.getenv("STORYBLOCKS_PRIVATE_KEY", "")
# free web image stock as a middle tier
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
# cheap image generation (nano-banana / gemini image, etc.) - optional
IMAGE_GEN_API_KEY = os.getenv("IMAGE_GEN_API_KEY", "")
IMAGE_GEN_MODEL = os.getenv("IMAGE_GEN_MODEL", "gemini-2.5-flash-image")
# ai video gen is a deliberate last resort; off unless a key is set
AI_VIDEO_GEN_API_KEY = os.getenv("AI_VIDEO_GEN_API_KEY", "")

# --- rendering ----------------------------------------------------------
OUTPUT_WIDTH = int(os.getenv("OUTPUT_WIDTH", "1920"))
OUTPUT_HEIGHT = int(os.getenv("OUTPUT_HEIGHT", "1080"))
OUTPUT_FPS = int(os.getenv("OUTPUT_FPS", "30"))

# How many b-roll seconds we allow the paid tiers to cover before falling
# back to Ken-Burns stills, as a cost guardrail per render.
MAX_AI_VIDEO_SECONDS = float(os.getenv("MAX_AI_VIDEO_SECONDS", "10"))


def enabled_asset_sources() -> list[str]:
    """Which tiers of the fallback ladder are usable given current keys."""
    sources: list[str] = []
    if STORYBLOCKS_PUBLIC_KEY and STORYBLOCKS_PRIVATE_KEY:
        sources.append("storyblocks")
    if PEXELS_API_KEY:
        sources.append("web_image")
    if IMAGE_GEN_API_KEY:
        sources.append("cheap_image_gen")
    if AI_VIDEO_GEN_API_KEY:
        sources.append("ai_video_gen")
    return sources
