"""Step 3 - source a visual for each b-roll cue, cheapest source first.

Fallback ladder (from the style preset's asset_priority):
    1. storyblocks      (subscribed -> free marginal cost, real footage)
    2. web_image        (free stock stills, animated later via Ken Burns)
    3. cheap_image_gen  (custom stills, ~cents each)
    4. ai_video_gen     (last resort, budget-capped)

Each source is best-effort: if a key is missing or the call fails, we fall
through to the next tier. Stills get `asset_is_video=False` so the compositor
applies Ken Burns; video clips get `asset_is_video=True`.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path

import httpx

from .. import config
from .models import Cue, EditDecisionList

_LADDER = ["storyblocks", "web_image", "cheap_image_gen", "ai_video_gen"]


def _cache_path(cue: Cue, ext: str) -> Path:
    key = hashlib.sha1((cue.query or "").encode()).hexdigest()[:16]
    return config.WORK_DIR / f"asset_{key}{ext}"


def _download(url: str, dest: Path) -> bool:
    try:
        with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return dest.stat().st_size > 0
    except Exception:
        return False


# --- tier 1: Storyblocks -------------------------------------------------
def _storyblocks(cue: Cue) -> tuple[str, bool] | None:
    if not (config.STORYBLOCKS_PUBLIC_KEY and config.STORYBLOCKS_PRIVATE_KEY):
        return None
    # Storyblocks signs each request: HMAC-SHA256(private_key+expires, resource).
    resource = "/api/v2/videos/search"
    expires = str(int(time.time()) + 100)
    hmac_key = config.STORYBLOCKS_PRIVATE_KEY + expires
    signature = hmac.new(
        hmac_key.encode(), resource.encode(), hashlib.sha256
    ).hexdigest()
    params = {
        "APIKEY": config.STORYBLOCKS_PUBLIC_KEY,
        "EXPIRES": expires,
        "HMAC": signature,
        "keywords": cue.query,
        "content_type": "footage",
        "results_per_page": 1,
    }
    try:
        r = httpx.get(
            f"https://api.storyblocks.com{resource}", params=params, timeout=30
        )
        r.raise_for_status()
        results = r.json().get("results") or r.json().get("info", {}).get("results")
        if not results:
            return None
        url = results[0].get("preview_urls", {}).get("_720p") or results[0].get(
            "preview_url"
        )
        if not url:
            return None
        dest = _cache_path(cue, ".mp4")
        return (str(dest), True) if _download(url, dest) else None
    except Exception:
        return None


# --- tier 2: free web stock stills (Pexels) ------------------------------
def _web_image(cue: Cue) -> tuple[str, bool] | None:
    if not config.PEXELS_API_KEY:
        return None
    try:
        r = httpx.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": config.PEXELS_API_KEY},
            params={"query": cue.query, "per_page": 1},
            timeout=30,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return None
        url = photos[0]["src"]["large2x"]
        dest = _cache_path(cue, ".jpg")
        return (str(dest), False) if _download(url, dest) else None
    except Exception:
        return None


# --- tier 3: cheap image generation --------------------------------------
def _cheap_image_gen(cue: Cue) -> tuple[str, bool] | None:
    if not config.IMAGE_GEN_API_KEY:
        return None
    # Provider-agnostic hook. Wire your image API here (nano-banana / Gemini
    # image, etc.); it should write a still to `dest` and return the path.
    from .imagegen import generate_still

    dest = _cache_path(cue, ".png")
    return (str(dest), False) if generate_still(cue.query, dest) else None


# --- tier 4: ai video gen (last resort, budget-capped) -------------------
_ai_video_budget = {"used": 0.0}


def _ai_video_gen(cue: Cue) -> tuple[str, bool] | None:
    if not config.AI_VIDEO_GEN_API_KEY:
        return None
    span = max(cue.end - cue.start, 1.0)
    if _ai_video_budget["used"] + span > config.MAX_AI_VIDEO_SECONDS:
        return None  # over the per-render cap; fall back to a still
    from .videogen import generate_clip

    dest = _cache_path(cue, ".mp4")
    if generate_clip(cue.query, span, dest):
        _ai_video_budget["used"] += span
        return str(dest), True
    return None


_SOURCES = {
    "storyblocks": _storyblocks,
    "web_image": _web_image,
    "cheap_image_gen": _cheap_image_gen,
    "ai_video_gen": _ai_video_gen,
}


def _order_for(cue: Cue) -> list[str]:
    """Honour the director's `prefer_source`, then the standard ladder."""
    order = list(_LADDER)
    if cue.prefer_source and cue.prefer_source in order:
        order.remove(cue.prefer_source)
        order.insert(0, cue.prefer_source)
    return order


def source_assets(edl: EditDecisionList) -> EditDecisionList:
    _ai_video_budget["used"] = 0.0
    for cue in edl.broll_cues():
        if not cue.query:
            continue
        for source in _order_for(cue):
            result = _SOURCES[source](cue)
            if result:
                cue.asset_path, cue.asset_is_video = result
                cue.asset_source = source
                break
    return edl
