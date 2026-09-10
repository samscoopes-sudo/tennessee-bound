#!/usr/bin/env python3
"""Space niche faceless YouTube video pipeline.

Uses Pexels + Pixabay for stock footage (images & videos).
Uses Gemini 2.5 TTS (Puck voice) for voiceover.
Assembly via ffmpeg with Ken Burns effects and hard cuts.

Usage:
  python space_video.py --script "Your voiceover script here"
  python space_video.py --script-file script.txt
  python space_video.py --assemble-only
"""
import argparse, subprocess, random, json, time, hashlib, os
from pathlib import Path

import requests

OUT = Path("space_output")
OUT.mkdir(exist_ok=True)

FPS = 24
VIDEO_W, VIDEO_H = 1920, 1080

PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
GOOGLE_KEY = os.environ.get("GOOGLE_KEY", "")


# ---------------------------------------------------------------------------
# Stock footage clients
# ---------------------------------------------------------------------------

class Pexels:
    BASE = "https://api.pexels.com"

    def __init__(self, key: str):
        self.headers = {"Authorization": key}
        self._used_ids: set[str] = set()

    def search_videos(self, query: str, per_page: int = 15, page: int = 1) -> list[dict]:
        r = requests.get(f"{self.BASE}/videos/search",
                         params={"query": query, "per_page": per_page, "page": page,
                                 "orientation": "landscape", "size": "medium"},
                         headers=self.headers)
        r.raise_for_status()
        results = []
        for v in r.json().get("videos", []):
            vid = f"pexels_v_{v['id']}"
            if vid in self._used_ids:
                continue
            files = sorted(v.get("video_files", []),
                           key=lambda f: abs((f.get("width", 0)) - 1920))
            if files:
                results.append({"id": vid, "url": files[0]["link"],
                                "width": files[0].get("width", 0),
                                "type": "video", "source": "pexels"})
        return results

    def search_images(self, query: str, per_page: int = 15, page: int = 1) -> list[dict]:
        r = requests.get(f"{self.BASE}/v1/search",
                         params={"query": query, "per_page": per_page, "page": page,
                                 "orientation": "landscape", "size": "large"},
                         headers=self.headers)
        r.raise_for_status()
        results = []
        for p in r.json().get("photos", []):
            pid = f"pexels_i_{p['id']}"
            if pid in self._used_ids:
                continue
            results.append({"id": pid, "url": p["src"]["large2x"],
                            "width": p.get("width", 0),
                            "type": "image", "source": "pexels"})
        return results

    def mark_used(self, item_id: str):
        self._used_ids.add(item_id)


class Pixabay:
    BASE = "https://pixabay.com/api"

    def __init__(self, key: str):
        self.key = key
        self._used_ids: set[str] = set()

    def search_videos(self, query: str, per_page: int = 15, page: int = 1) -> list[dict]:
        r = requests.get(f"{self.BASE}/videos/",
                         params={"key": self.key, "q": query, "per_page": per_page,
                                 "page": page, "orientation": "horizontal",
                                 "safesearch": "true"})
        r.raise_for_status()
        results = []
        for v in r.json().get("hits", []):
            vid = f"pixabay_v_{v['id']}"
            if vid in self._used_ids:
                continue
            vids = v.get("videos", {})
            best = vids.get("large", vids.get("medium", {}))
            if best.get("url"):
                results.append({"id": vid, "url": best["url"],
                                "width": best.get("width", 0),
                                "type": "video", "source": "pixabay"})
        return results

    def search_images(self, query: str, per_page: int = 15, page: int = 1) -> list[dict]:
        r = requests.get(f"{self.BASE}/",
                         params={"key": self.key, "q": query, "per_page": per_page,
                                 "page": page, "orientation": "horizontal",
                                 "image_type": "photo", "safesearch": "true"})
        r.raise_for_status()
        results = []
        for p in r.json().get("hits", []):
            pid = f"pixabay_i_{p['id']}"
            if pid in self._used_ids:
                continue
            results.append({"id": pid, "url": p.get("largeImageURL", p.get("webformatURL", "")),
                            "width": p.get("imageWidth", 0),
                            "type": "image", "source": "pixabay"})
        return results

    def mark_used(self, item_id: str):
        self._used_ids.add(item_id)


def download_asset(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return dest


def fetch_unique_asset(query: str, pexels: Pexels | None, pixabay: Pixabay | None,
                       asset_type: str = "video", dest: Path = None) -> Path | None:
    """Fetch one unique asset matching query. Tries available sources."""
    all_used: set[str] = set()
    if pexels:
        all_used |= pexels._used_ids
    if pixabay:
        all_used |= pixabay._used_ids

    for page in range(1, 4):
        results = []
        if asset_type == "video":
            if pexels:
                try:
                    results += pexels.search_videos(query, page=page)
                except Exception:
                    pass
            if pixabay:
                try:
                    results += pixabay.search_videos(query, page=page)
                except Exception:
                    pass
        else:
            if pexels:
                try:
                    results += pexels.search_images(query, page=page)
                except Exception:
                    pass
            if pixabay:
                try:
                    results += pixabay.search_images(query, page=page)
                except Exception:
                    pass

        for item in results:
            if item["id"] not in all_used:
                ext = ".mp4" if asset_type == "video" else ".jpg"
                if dest is None:
                    dest = OUT / f"{item['id']}{ext}"
                if dest.exists() and dest.stat().st_size > 0:
                    all_used.add(item["id"])
                    if pexels:
                        pexels.mark_used(item["id"])
                    if pixabay:
                        pixabay.mark_used(item["id"])
                    return dest
                try:
                    download_asset(item["url"], dest)
                    all_used.add(item["id"])
                    if pexels:
                        pexels.mark_used(item["id"])
                    if pixabay:
                        pixabay.mark_used(item["id"])
                    return dest
                except Exception as e:
                    print(f"    Download failed ({item['source']}): {e}")
                    continue
    return None


# ---------------------------------------------------------------------------
# Gemini TTS
# ---------------------------------------------------------------------------

def _tts_chunk(text: str, dest: Path, model: str = "gemini-2.5-flash-preview-tts"):
    """Generate audio for one chunk of text via Gemini TTS."""
    import base64
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_KEY}"
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Puck"}
                }
            }
        }
    }
    r = requests.post(url, json=body, timeout=300)
    if not r.ok:
        raise RuntimeError(f"Gemini TTS failed: {r.status_code} {r.text[:500]}")
    data = r.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates: {data}")
    for part in candidates[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData", {})
        if inline.get("data"):
            audio_bytes = base64.b64decode(inline["data"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(audio_bytes)
            return dest
    raise RuntimeError(f"No audio data in response")


def generate_voiceover(script: str, dest: Path):
    """Generate voiceover using Gemini TTS, splitting into paragraph chunks."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"Voiceover exists: {dest}")
        return dest

    # Split script into paragraphs to stay within limits
    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [script]

    print(f"Generating voiceover via Gemini TTS ({len(paragraphs)} chunks)...")
    chunk_files = []

    for i, para in enumerate(paragraphs):
        chunk_dest = OUT / f"vo_chunk_{i:02d}.wav"
        if chunk_dest.exists() and chunk_dest.stat().st_size > 0:
            print(f"  [chunk {i}] skip (cached)")
            chunk_files.append(chunk_dest)
            continue
        print(f"  [chunk {i}] generating ({len(para)} chars)...")
        _tts_chunk(para, chunk_dest)
        chunk_files.append(chunk_dest)
        print(f"  [chunk {i}] OK")

    # Concat all chunks
    if len(chunk_files) == 1:
        import shutil
        shutil.copy2(chunk_files[0], dest)
    else:
        listfile = OUT / "vo_chunks_list.txt"
        listfile.write_text("".join(f"file '{f.resolve()}'\n" for f in chunk_files))
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
            "-c:a", "pcm_s16le", str(dest)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"Voiceover saved: {dest}")
    return dest


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

def _ken_burns(image_path: Path, dest: Path, duration: float):
    styles = [
        f"zoompan=z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='if(lte(zoom,1.0),1.3,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='min(zoom+0.001,1.2)':x='if(lte(on,1),0,x+1)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='min(zoom+0.001,1.2)':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),0,y+1)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)+sin(on/30)*20':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
    ]
    vf = f"{random.choice(styles)},format=yuv420p"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _scale_video(src: Path, dest: Path, duration: float):
    subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-t", str(duration),
        "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _black_frame(dest: Path, duration: float):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"color=c=black:s={VIDEO_W}x{VIDEO_H}:r={FPS}:d={duration}",
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18",
        str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_duration(path: Path) -> float:
    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Segment building
# ---------------------------------------------------------------------------

SEGMENT_QUERIES = [
    "nebula deep space", "planet earth from space", "rocket launch",
    "milky way night sky", "aurora borealis timelapse", "astronaut spacewalk",
    "saturn rings", "moon surface closeup", "solar flare sun",
    "international space station", "galaxy spiral", "comet tail",
    "mars surface red planet", "stars timelapse", "space shuttle",
    "black hole visualization", "jupiter great red spot", "meteor shower",
    "telescope observatory", "earth sunrise orbit", "lunar eclipse",
    "space rocket engine fire", "venus planet", "constellation stars",
    "northern lights green", "earth clouds atmosphere", "mercury planet surface",
    "supernova explosion", "space station interior", "pluto dwarf planet",
    "andromeda galaxy", "star field deep space", "rocket booster separation",
    "earth night city lights", "solar system planets", "nebula colorful gas",
    "asteroid belt space", "space debris orbit", "mars rover",
    "eclipse solar corona", "uranus planet blue", "milky way center",
    "spaceship cockpit", "earth ocean from space", "neptune planet",
    "lunar surface craters", "satellite orbit earth", "cosmic dust cloud",
    "space exploration historic", "sunrise from orbit golden",
]


def fetch_segments(segment_count: int, pexels: Pexels, pixabay: Pixabay,
                   prefer_video: bool = True):
    """Fetch unique stock assets for each segment."""
    assets_dir = OUT / "assets"
    assets_dir.mkdir(exist_ok=True)

    manifest_path = OUT / "asset_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = []

    existing = len(manifest)
    if existing >= segment_count:
        print(f"Already have {existing} assets (need {segment_count}), skipping fetch.")
        return manifest

    queries = SEGMENT_QUERIES.copy()
    random.shuffle(queries)

    for i in range(existing, segment_count):
        query = queries[i % len(queries)]
        idx = f"{i:03d}"
        print(f"  [seg_{idx}] searching: '{query}'...")

        asset_path = None
        asset_type = "video" if prefer_video else "image"

        # Try video first, fall back to image
        if prefer_video:
            vdest = assets_dir / f"seg_{idx}.mp4"
            asset_path = fetch_unique_asset(query, pexels, pixabay, "video", vdest)
            if asset_path:
                asset_type = "video"

        if not asset_path:
            idest = assets_dir / f"seg_{idx}.jpg"
            asset_path = fetch_unique_asset(query, pexels, pixabay, "image", idest)
            asset_type = "image"

        if asset_path:
            manifest.append({"index": i, "query": query, "type": asset_type,
                             "path": str(asset_path)})
            print(f"  [seg_{idx}] OK ({asset_type})")
        else:
            print(f"  [seg_{idx}] FAILED - no results for '{query}'")
            manifest.append({"index": i, "query": query, "type": "black", "path": ""})

        manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def assemble(manifest: list[dict], voiceover_path: Path | None, seg_dur: float = 4.0):
    """Assemble segments into final video."""
    segments = []

    for entry in manifest:
        i = entry["index"]
        seg_dest = OUT / f"seg_{i:03d}_final.mp4"

        if seg_dest.exists() and seg_dest.stat().st_size > 0:
            segments.append(seg_dest)
            print(f"  [seg_{i:03d}] skip (cached)")
            continue

        if entry["type"] == "black" or not entry["path"]:
            _black_frame(seg_dest, seg_dur)
        elif entry["type"] == "image":
            _ken_burns(Path(entry["path"]), seg_dest, seg_dur)
        elif entry["type"] == "video":
            _scale_video(Path(entry["path"]), seg_dest, seg_dur)

        segments.append(seg_dest)
        print(f"  [seg_{i:03d}] OK ({entry['type']})")

    # Concat
    listfile = OUT / "segments_list.txt"
    listfile.write_text("".join(f"file '{s.resolve()}'\n" for s in segments))

    video_only = OUT / "space_video_noaudio.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        str(video_only)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"\nVideo assembled (no audio): {video_only}")

    # Merge voiceover
    if voiceover_path and voiceover_path.exists():
        final = OUT / "space_video_final.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video_only), "-i", str(voiceover_path),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Final video with voiceover: {final}")
    else:
        print("No voiceover found. Run with --script to generate one.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pexels-key", type=str, help="Pexels API key (or set PEXELS_KEY env)")
    ap.add_argument("--pixabay-key", type=str, help="Pixabay API key (or set PIXABAY_KEY env)")
    ap.add_argument("--google-key", type=str, help="Google API key for Gemini TTS (or set GOOGLE_KEY env)")
    ap.add_argument("--script", type=str, help="Voiceover script text")
    ap.add_argument("--script-file", type=str, help="Path to voiceover script file")
    ap.add_argument("--segments", type=int, default=75, help="Number of visual segments")
    ap.add_argument("--seg-dur", type=float, default=4.0, help="Seconds per segment")
    ap.add_argument("--prefer-images", action="store_true",
                    help="Prefer images over video clips")
    ap.add_argument("--fetch-only", action="store_true", help="Only fetch assets")
    ap.add_argument("--tts-only", action="store_true", help="Only generate voiceover")
    ap.add_argument("--assemble-only", action="store_true", help="Only assemble")
    args = ap.parse_args()

    global PEXELS_KEY, PIXABAY_KEY, GOOGLE_KEY
    if args.pexels_key:
        PEXELS_KEY = args.pexels_key
    if args.pixabay_key:
        PIXABAY_KEY = args.pixabay_key
    if args.google_key:
        GOOGLE_KEY = args.google_key

    if not args.assemble_only and not args.tts_only and not PEXELS_KEY and not PIXABAY_KEY:
        print("ERROR: At least one stock API key required (--pexels-key/--pixabay-key or env vars)")
        return

    total_dur = args.segments * args.seg_dur
    print(f"Target: {args.segments} segments x {args.seg_dur}s = {total_dur:.0f}s ({total_dur/60:.1f} min)")

    pexels = Pexels(PEXELS_KEY) if PEXELS_KEY else None
    pixabay = Pixabay(PIXABAY_KEY) if PIXABAY_KEY else None
    sources = []
    if pexels:
        sources.append("Pexels")
    if pixabay:
        sources.append("Pixabay")
    print(f"Stock sources: {', '.join(sources)}")

    # Load or fetch script
    script = None
    if args.script:
        script = args.script
    elif args.script_file:
        script = Path(args.script_file).read_text()

    voiceover_path = OUT / "voiceover.wav"

    if args.tts_only:
        if not script:
            print("ERROR: --script or --script-file required for TTS")
            return
        generate_voiceover(script, voiceover_path)
        return

    if args.assemble_only:
        manifest_path = OUT / "asset_manifest.json"
        if not manifest_path.exists():
            print("ERROR: No asset manifest. Run without --assemble-only first.")
            return
        manifest = json.loads(manifest_path.read_text())
        assemble(manifest, voiceover_path, args.seg_dur)
        return

    # Generate voiceover if script provided
    if script and not voiceover_path.exists():
        generate_voiceover(script, voiceover_path)

    # Fetch assets
    print(f"\n=== FETCHING {args.segments} STOCK ASSETS ===")
    manifest = fetch_segments(args.segments, pexels, pixabay,
                              prefer_video=not args.prefer_images)

    if not args.fetch_only:
        print(f"\n=== ASSEMBLING VIDEO ===")
        assemble(manifest, voiceover_path, args.seg_dur)


if __name__ == "__main__":
    main()
