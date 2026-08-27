"""Stock-footage-only pipeline: shot-list + Pexels API -> downloaded clips -> assembled video.

No ComfyUI or GPU needed. Searches Pexels for each b-roll shot, downloads the
best-match clip, and hands everything to the assembler.

Usage:
  python run.py stock-edit --channel tennessee-bound --run tennessee-towns-hidden-costs
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

from . import config

PEXELS_BASE = "https://api.pexels.com/videos/search"

_STOP = {
    "a", "an", "the", "of", "with", "on", "in", "and", "from", "by", "at", "to",
    "old", "close", "closeup", "up", "shot", "small", "few", "some", "very",
    "weathered", "rustic", "vintage", "dim", "empty", "s", "no", "not",
}


def _query(subject: str) -> str:
    subject = subject.split(",")[0]
    words = re.findall(r"[a-zA-Z]+", subject.lower())
    kept = [w for w in words if w not in _STOP]
    return " ".join(kept[:5]) or subject.strip()


def _best_video(query: str, api_key: str, min_dur: float,
                want_w: int = 1920, want_h: int = 1080) -> str | None:
    """Search Pexels and return the download URL of the best-match clip, or None."""
    try:
        r = requests.get(PEXELS_BASE,
                         headers={"Authorization": api_key},
                         params={"query": query, "orientation": "landscape",
                                 "per_page": 15, "size": "medium"},
                         timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    Pexels search failed: {e}")
        return None

    best_score, best_url = -1.0, None
    for v in r.json().get("videos", []):
        dur = float(v.get("duration") or 0)
        for f in v.get("video_files", []):
            if f.get("file_type") != "video/mp4":
                continue
            w = int(f.get("width") or 0)
            h = int(f.get("height") or 0)
            if w < want_w * 0.5:
                continue
            score = 0.0
            if dur >= min_dur:
                score += 3
            if h and abs((w / h) - 16 / 9) < 0.12:
                score += 1
            score += min(w, 3840) / 3840
            if score > best_score:
                best_score, best_url = score, f.get("link")
    return best_url


def _download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"    download failed: {e}")
        return False


def fetch_stock(shots_path: Path, api_key: str, out_dir: Path,
                limit: int | None = None, start: int = 0,
                force: bool = False) -> int:
    """Download Pexels clips for every b-roll shot. Returns count of clips fetched."""
    plan = json.loads(shots_path.read_text())
    shots = plan["shots"]
    out_dir.mkdir(parents=True, exist_ok=True)

    fetched = 0
    for s in shots:
        idx = s["index"]
        if idx < start:
            continue
        if limit is not None and fetched >= limit:
            break
        if s["kind"] != "broll":
            continue

        dest = out_dir / f"br_{idx:04d}.mp4"
        if dest.exists() and not force:
            s["asset"] = str(dest)
            print(f"  [{idx:>3}] skip (exists): {dest.name}")
            continue

        subject = s.get("subject", s.get("prompt", ""))
        q = _query(subject)
        dur = float(s.get("duration", 3.5))
        print(f"  [{idx:>3}] search: '{q}' ({dur:.1f}s) ...", end=" ", flush=True)

        url = _best_video(q, api_key, dur)
        if not url:
            print("NO MATCH")
            continue

        if _download(url, dest):
            s["asset"] = str(dest)
            fetched += 1
            sz = dest.stat().st_size / 1024 / 1024
            print(f"OK ({sz:.1f} MB)")
        else:
            print("FAILED")

        time.sleep(0.2)

    shots_path.write_text(json.dumps(plan, indent=2))
    print(f"\nFetched {fetched} clips. Shot-list updated with asset paths.")
    return fetched
