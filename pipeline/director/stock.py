"""Real stock b-roll from multiple free libraries (Pexels + Pixabay), so atmospheric
shots look like genuine footage instead of AI. Returns None when nothing fits ->
caller falls back to AI generation.

Free keys (set in your OWN terminal, never paste into chat):
  export PEXELS_API_KEY=...     # https://www.pexels.com/api/
  export PIXABAY_API_KEY=...    # https://pixabay.com/api/docs/

Pulling from two independent libraries (and picking the best match across both)
means far less overlap with the clips every other channel uses.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import requests

_STOP = {
    "a", "an", "the", "of", "with", "on", "in", "and", "from", "by", "at", "to",
    "old", "close", "closeup", "up", "shot", "small", "few", "some", "very",
    "weathered", "rustic", "vintage", "dim", "empty", "s",
}


def enabled() -> bool:
    return bool(os.environ.get("PEXELS_API_KEY") or os.environ.get("PIXABAY_API_KEY"))


def query_from_subject(subject: str) -> str:
    subject = subject.split(",")[0]                      # bare subject, drop style suffix
    words = re.findall(r"[a-zA-Z]+", subject.lower())
    kept = [w for w in words if w not in _STOP]
    return " ".join(kept[:5]) or subject.strip()


def _score(w: int, h: int, dur: float, min_dur: float, want_w: int) -> float:
    s = 0.0
    if dur >= min_dur:
        s += 2
    if h and abs((w / h) - 16 / 9) < 0.12:
        s += 1
    s += min(w, 3840) / 3840
    return s


def _candidates_pexels(query: str, key: str, min_dur: float, want_w: int, want_h: int) -> list[tuple]:
    r = requests.get("https://api.pexels.com/videos/search",
                     headers={"Authorization": key},
                     params={"query": query, "orientation": "landscape",
                             "per_page": 10, "size": "medium"}, timeout=30)
    r.raise_for_status()
    out = []
    for v in r.json().get("videos", []):
        dur = float(v.get("duration") or 0)
        for f in v.get("video_files", []):
            if f.get("file_type") != "video/mp4":
                continue
            w, h = int(f.get("width") or 0), int(f.get("height") or 0)
            if w >= want_w and h >= want_h * 0.9:
                out.append((_score(w, h, dur, min_dur, want_w), f.get("link"), "pexels"))
    return out


def _candidates_pixabay(query: str, key: str, min_dur: float, want_w: int, want_h: int) -> list[tuple]:
    r = requests.get("https://pixabay.com/api/videos/",
                     params={"key": key, "q": query, "video_type": "film", "per_page": 20},
                     timeout=30)
    r.raise_for_status()
    out = []
    for v in r.json().get("hits", []):
        dur = float(v.get("duration") or 0)
        for stream in v.get("videos", {}).values():
            w, h = int(stream.get("width") or 0), int(stream.get("height") or 0)
            link = stream.get("url")
            if link and w >= want_w and h >= want_h * 0.9:
                out.append((_score(w, h, dur, min_dur, want_w), link, "pixabay"))
    return out


def fetch(subject: str, duration: float, dest: Path, want_w: int, want_h: int) -> Path | None:
    """Download the best-matching real stock clip across all configured libraries,
    or None to signal AI fallback. Returns the chosen provider via dest sidecar? No —
    caller sets shot['source']; provider name is in the printed log only."""
    if not enabled():
        return None
    q = query_from_subject(subject)
    cands: list[tuple] = []
    pex, pix = os.environ.get("PEXELS_API_KEY"), os.environ.get("PIXABAY_API_KEY")
    for get, key in ((_candidates_pexels, pex), (_candidates_pixabay, pix)):
        if not key:
            continue
        try:
            cands += get(q, key, duration, want_w, want_h)
        except Exception:
            pass
    if not cands:
        return None
    cands.sort(key=lambda c: c[0], reverse=True)
    link = cands[0][1]
    try:
        r = requests.get(link, timeout=180)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest
    except Exception:
        return None
