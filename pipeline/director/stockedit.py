"""Stock-footage-only pipeline: multi-source search -> downloaded clips -> assembled video.

Searches Pexels (video + photo), Wikimedia Commons, and Google Images for each
b-roll shot. Downloads the best-match clip and hands everything to the assembler.

Usage:
  python run.py stock-edit --channel tennessee-bound --run plumbing-tips
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
from pathlib import Path

import requests

from . import config

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

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
    try:
        r = requests.get(PEXELS_VIDEO_URL,
                         headers={"Authorization": api_key},
                         params={"query": query, "orientation": "landscape",
                                 "per_page": 15, "size": "medium"},
                         timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    Pexels video search failed: {e}")
        return None

    best_score, best_url = -1.0, None
    for v in r.json().get("videos", []):
        dur = float(v.get("duration") or 0)
        for f in v.get("video_files", []):
            if f.get("file_type") != "video/mp4":
                continue
            w = int(f.get("width") or 0)
            h = int(f.get("height") or 0)
            if w < want_w * 0.5 or w > want_w:
                continue
            score = 0.0
            if dur >= min_dur:
                score += 3
            if h and abs((w / h) - 16 / 9) < 0.12:
                score += 1
            score += min(w, want_w) / want_w
            if score > best_score:
                best_score, best_url = score, f.get("link")
    return best_url


def _best_photo(query: str, api_key: str,
                want_w: int = 1920, want_h: int = 1080) -> str | None:
    try:
        r = requests.get(PEXELS_PHOTO_URL,
                         headers={"Authorization": api_key},
                         params={"query": query, "orientation": "landscape",
                                 "per_page": 15},
                         timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    Pexels photo search failed: {e}")
        return None

    best_score, best_url = -1.0, None
    for p in r.json().get("photos", []):
        w = int(p.get("width") or 0)
        h = int(p.get("height") or 0)
        if w < want_w * 0.5:
            continue
        score = 0.0
        if h and abs((w / h) - 16 / 9) < 0.15:
            score += 2
        score += min(w, want_w) / want_w
        src = p.get("src", {})
        url = src.get("large2x") or src.get("large") or src.get("original")
        if url and score > best_score:
            best_score, best_url = score, url
    return best_url


def _wikimedia_image(query: str, want_w: int = 1920) -> str | None:
    """Search Wikimedia Commons for a freely-licensed image."""
    try:
        r = requests.get(WIKIMEDIA_API, params={
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": "6",
            "gsrlimit": "10",
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": str(want_w),
            "format": "json",
        }, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    Wikimedia search failed: {e}")
        return None

    pages = r.json().get("query", {}).get("pages", {})
    best_score, best_url = -1.0, None
    for p in pages.values():
        for ii in p.get("imageinfo", []):
            mime = ii.get("mime", "")
            if not mime.startswith("image/"):
                continue
            w = int(ii.get("width") or 0)
            h = int(ii.get("height") or 0)
            if w < want_w * 0.4 or w > want_w:
                continue
            score = 0.0
            if h and abs((w / h) - 16 / 9) < 0.2:
                score += 2
            score += min(w, want_w) / want_w
            url = ii.get("thumburl") or ii.get("url")
            if url and score > best_score:
                best_score, best_url = score, url
    return best_url


def _google_image(query: str, api_key: str, cse_id: str,
                  want_w: int = 1920) -> str | None:
    """Search Google Custom Search for an image."""
    try:
        r = requests.get(GOOGLE_CSE_URL, params={
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "searchType": "image",
            "imgSize": "xlarge",
            "imgType": "photo",
            "num": 10,
        }, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    Google image search failed: {e}")
        return None

    best_score, best_url = -1.0, None
    for item in r.json().get("items", []):
        img = item.get("image", {})
        w = int(img.get("width") or 0)
        h = int(img.get("height") or 0)
        if w < want_w * 0.4 or w > want_w:
            continue
        score = 0.0
        if h and abs((w / h) - 16 / 9) < 0.2:
            score += 2
        score += min(w, want_w) / want_w
        url = item.get("link")
        if url and score > best_score:
            best_score, best_url = score, url
    return best_url


MAX_FILE_MB = 30

def _download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=180, stream=True)
        r.raise_for_status()
        size = int(r.headers.get("content-length", 0))
        if size > MAX_FILE_MB * 1024 * 1024:
            print(f"    skip ({size / 1024 / 1024:.0f} MB > {MAX_FILE_MB} MB limit)")
            r.close()
            return False
        data = r.content
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"    download failed: {e}")
        return False


def fetch_stock(shots_path: Path, api_key: str, out_dir: Path,
                limit: int | None = None, start: int = 0,
                force: bool = False,
                google_api_key: str | None = None,
                google_cse_id: str | None = None,
                photos_only: bool = False) -> int:
    """Download clips for every b-roll shot from multiple sources. Returns count fetched."""
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

        dest_mp4 = out_dir / f"br_{idx:04d}.mp4"
        dest_jpg = out_dir / f"br_{idx:04d}.jpg"
        if (dest_mp4.exists() or dest_jpg.exists()) and not force:
            s["asset"] = str(dest_mp4 if dest_mp4.exists() else dest_jpg)
            print(f"  [{idx:>3}] skip (exists)")
            continue

        subject = s.get("subject", s.get("prompt", ""))
        q = _query(subject)
        dur = float(s.get("duration", 3.5))
        print(f"  [{idx:>3}] search: '{q}' ({dur:.1f}s) ...", end=" ", flush=True)

        # 1. Pexels video (skipped in photos-only mode)
        if not photos_only:
            url = _best_video(q, api_key, dur)
            if url:
                if _download(url, dest_mp4):
                    s["asset"] = str(dest_mp4)
                    s["source"] = "pexels_video"
                    fetched += 1
                    sz = dest_mp4.stat().st_size / 1024 / 1024
                    print(f"PEXELS VIDEO ({sz:.1f} MB)")
                    time.sleep(0.2)
                    continue

        # 2. Pexels photo
        url = _best_photo(q, api_key)
        if url:
            if _download(url, dest_jpg):
                s["asset"] = str(dest_jpg)
                s["source"] = "pexels_photo"
                fetched += 1
                sz = dest_jpg.stat().st_size / 1024 / 1024
                print(f"PEXELS PHOTO ({sz:.1f} MB)")
                time.sleep(0.2)
                continue

        # 3. Wikimedia Commons (no API key needed; skipped in photos-only mode)
        if not photos_only:
            url = _wikimedia_image(q)
            if url:
                if _download(url, dest_jpg):
                    s["asset"] = str(dest_jpg)
                    s["source"] = "wikimedia"
                    fetched += 1
                    sz = dest_jpg.stat().st_size / 1024 / 1024
                    print(f"WIKIMEDIA ({sz:.1f} MB)")
                    time.sleep(0.2)
                    continue

        # 4. Google Images (needs API key + CSE ID; skipped in photos-only mode)
        if not photos_only and google_api_key and google_cse_id:
            url = _google_image(q, google_api_key, google_cse_id)
            if url:
                if _download(url, dest_jpg):
                    s["asset"] = str(dest_jpg)
                    s["source"] = "google_image"
                    fetched += 1
                    sz = dest_jpg.stat().st_size / 1024 / 1024
                    print(f"GOOGLE IMAGE ({sz:.1f} MB)")
                    time.sleep(0.2)
                    continue

        print("NO MATCH")
        time.sleep(0.2)

    shots_path.write_text(json.dumps(plan, indent=2))
    print(f"\nFetched {fetched} clips. Shot-list updated with asset paths.")
    return fetched
