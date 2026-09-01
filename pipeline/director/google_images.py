"""Google Images scraper for b-roll stills.

Searches Google Images for a query and downloads the first usable result.
Uses requests with a browser user-agent to fetch search results.
"""
from __future__ import annotations

import re
import time
import random
from pathlib import Path

import requests

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({"User-Agent": _UA})
    return _SESSION


def search_and_download(query: str, dest: Path, min_width: int = 1280) -> Path:
    """Search Google Images for `query` and save the first large result to `dest`."""
    s = _get_session()
    params = {
        "q": query,
        "tbm": "isch",
        "tbs": f"isz:lt,islt:2mp",  # large images only
    }
    r = s.get("https://www.google.com/search", params=params, timeout=15)
    r.raise_for_status()

    urls = re.findall(r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', r.text)
    urls = [u for u in urls if "gstatic" not in u and "google" not in u]

    if not urls:
        urls = re.findall(r'(https?://\S+\.(?:jpg|jpeg|png|webp))', r.text)
        urls = [u for u in urls if "gstatic" not in u and "google" not in u and "favicon" not in u]

    if not urls:
        raise RuntimeError(f"No images found for: {query}")

    for url in urls[:10]:
        try:
            time.sleep(random.uniform(0.3, 0.8))
            img = s.get(url, timeout=15)
            img.raise_for_status()
            if len(img.content) < 10_000:
                continue
            dest.write_bytes(img.content)
            return dest
        except Exception:
            continue

    raise RuntimeError(f"Could not download any image for: {query}")
