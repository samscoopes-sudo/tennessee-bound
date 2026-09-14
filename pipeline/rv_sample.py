#!/usr/bin/env python3
"""RV Living sample pipeline — AI images + avatar talking head, assembled with ffmpeg.

Runs on RunPod (ComfyUI) for image generation & avatar lip-sync.
Uses Gemini TTS (Puck voice) for voiceover.
Phone-camera aesthetic: soft focus, foggy, not studio quality.

Usage:
    python rv_sample.py --comfy-url https://YOUR-POD.proxy.runpod.net \
                        --google-key AIza... \
                        --avatar avatar.png \
                        [--script-file scripts/rv_script.txt] \
                        [--assemble-only]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from director.comfy import Comfy

OUT = Path("rv_output")
FPS = 24
VIDEO_W, VIDEO_H = 1024, 576

AVATAR_W, AVATAR_H = 832, 480
AVATAR_FPS = 25
AVATAR_FRAMES = 81

PHONE_STYLE = (
    "candid amateur snapshot, shot on old smartphone, slightly soft focus, "
    "foggy atmosphere, warm muted tones, low contrast, slight lens haze, "
    "not professional, not studio lighting, not high definition"
)
NEGATIVE = (
    "studio lighting, professional camera, DSLR, sharp focus, HDR, "
    "high contrast, crisp details, 4K, 8K, cinematic, polished"
)

SCRIPT_DEFAULT = """Living in an RV full time sounds like a dream. No mortgage. No landlord. Just the open road and a new backyard every week.

But here's what nobody tells you. The first month is chaos. Your water pump breaks at two in the morning. You can't find a dump station. And your neighbor's generator sounds like a lawnmower factory.

I sold my house in Bakersfield three years ago. Bought a used Class C for twenty two thousand dollars. My wife thought I'd lost my mind. Maybe I did.

But waking up next to the Pacific Ocean on a Tuesday morning. Drinking coffee while elk graze outside your window in Yellowstone. Watching the sunset paint the desert outside Sedona. That changes you.

The money part surprises people. My total monthly costs run about fourteen hundred dollars. That's lot fees, insurance, fuel, food, everything. Back in California I was spending four thousand just on the basics.

Now I'm not gonna sugar coat it. RV living has real downsides. Space is tight. Things break constantly. You will have days where you want to quit and rent an apartment.

But three years in, I wouldn't trade it. Every morning I step outside and my office is whatever national forest or coastline I parked next to. That's worth every leaky faucet and blown tire.

If you're thinking about it, start small. Rent an RV for a month. Try it before you sell everything. Your future self will thank you either way."""


BEATS = [
    {"type": "avatar", "text": "intro — greeting the viewer"},
    {"type": "image", "prompt": "old recreational vehicle parked on empty desert highway, dust and morning fog, cracked asphalt, tumbleweeds"},
    {"type": "image", "prompt": "interior of cramped RV kitchen, dishes in tiny sink, dim yellow ceiling light, condensation on windows"},
    {"type": "image", "prompt": "broken water pump under RV cabinet, flashlight beam, tools scattered, middle of the night feel"},
    {"type": "avatar", "text": "mid — telling personal story, hand gestures"},
    {"type": "image", "prompt": "Pacific Ocean view from RV windshield, foggy morning, coffee mug on dashboard, condensation on glass"},
    {"type": "image", "prompt": "elk grazing in meadow seen through RV window, yellowstone, early morning mist, warm golden light through haze"},
    {"type": "image", "prompt": "desert sunset near Sedona Arizona, RV silhouette in foreground, orange and purple sky, dusty atmosphere"},
    {"type": "image", "prompt": "hand-written budget list on notebook page, calculator beside it, dim RV table lamp, shallow depth of field"},
    {"type": "avatar", "text": "mid — being honest about downsides, leaning forward"},
    {"type": "image", "prompt": "tiny cramped RV bathroom, towels hanging everywhere, foggy mirror, claustrophobic feeling"},
    {"type": "image", "prompt": "man sitting in camp chair outside RV, national forest behind him, morning fog between pine trees, coffee steam"},
    {"type": "avatar", "text": "outro — encouraging the viewer, warm smile"},
]


# ---------------------------------------------------------------------------
# Gemini TTS (reused from space_video)
# ---------------------------------------------------------------------------

def _tts_chunk(text: str, dest: Path, google_key: str,
               model: str = "gemini-2.5-flash-preview-tts"):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={google_key}")
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
    import requests, time as _time
    for attempt in range(5):
        r = requests.post(url, json=body, timeout=300)
        if r.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"    rate limited, waiting {wait}s...")
            _time.sleep(wait)
            continue
        if not r.ok:
            raise RuntimeError(f"Gemini TTS failed: {r.status_code} {r.text[:500]}")
        break
    else:
        raise RuntimeError("Gemini TTS rate limited after 5 retries")
    data = r.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates: {data}")
    for part in candidates[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData", {})
        if inline.get("data"):
            audio_bytes = base64.b64decode(inline["data"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            mime = inline.get("mimeType", "")
            raw_file = dest.with_suffix(".raw")
            raw_file.write_bytes(audio_bytes)
            # Parse sample rate from mime like "audio/L16;codec=pcm;rate=24000"
            rate = "24000"
            if "rate=" in mime:
                rate = mime.split("rate=")[-1].split(";")[0]
            is_raw_pcm = "L16" in mime or "pcm" in mime.lower()
            if is_raw_pcm:
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "s16be", "-ar", rate, "-ac", "1",
                    "-i", str(raw_file),
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                    str(dest)
                ]
            else:
                cmd = [
                    "ffmpeg", "-y", "-i", str(raw_file),
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                    str(dest)
                ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg convert ({mime}) failed: "
                    f"{result.stderr[-300:] if result.stderr else ''}")
            return dest
    raise RuntimeError("No audio data in response")


def generate_voiceover(script: str, google_key: str, out_dir: Path) -> Path:
    dest = out_dir / "voiceover.wav"
    if dest.exists() and dest.stat().st_size > 0:
        print(f"Voiceover cached: {dest}")
        return dest

    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [script]

    print(f"Generating voiceover ({len(paragraphs)} chunks via Gemini TTS)...")
    chunks = []
    for i, para in enumerate(paragraphs):
        chunk = out_dir / f"vo_chunk_{i:02d}.wav"
        if chunk.exists() and chunk.stat().st_size > 0:
            print(f"  [chunk {i}] cached")
        else:
            print(f"  [chunk {i}] generating ({len(para)} chars)...")
            _tts_chunk(para, chunk, google_key)
            print(f"  [chunk {i}] OK")
        chunks.append(chunk)

    # Normalize each chunk to proper WAV (Gemini returns raw audio data)
    norm_chunks = []
    for i, c in enumerate(chunks):
        normed = out_dir / f"vo_norm_{i:02d}.wav"
        if normed.exists() and normed.stat().st_size > 0:
            norm_chunks.append(normed)
            continue
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(c),
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(normed)
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  normalize chunk {i} failed: {result.stderr[-300:] if result.stderr else ''}")
            norm_chunks.append(c)
        else:
            norm_chunks.append(normed)

    if len(norm_chunks) == 1:
        shutil.copy2(norm_chunks[0], dest)
    else:
        inputs = []
        for c in norm_chunks:
            inputs.extend(["-i", str(c)])
        filter_str = f"concat=n={len(norm_chunks)}:v=0:a=1[out]"
        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_str, "-map", "[out]",
            "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1", str(dest)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ffmpeg concat failed (exit {result.returncode})")
            if result.stderr:
                print(result.stderr[-500:])
            shutil.copy2(norm_chunks[0], dest)
            print("Using first chunk only as fallback.")

    print(f"Voiceover saved: {dest} ({dest.stat().st_size / 1024:.0f} KB)")
    return dest


# ---------------------------------------------------------------------------
# AI image generation (ComfyUI flux_still with phone-camera prompts)
# ---------------------------------------------------------------------------

def generate_image(comfy: Comfy, prompt: str, dest: Path, seed: int = 0) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  image cached: {dest.name}")
        return dest
    full_prompt = f"{prompt}, {PHONE_STYLE}"
    print(f"  generating image: {prompt[:60]}...")
    comfy.flux_still(full_prompt, VIDEO_W, VIDEO_H, dest,
                     seed=seed, guidance=3.5, steps=20)
    print(f"  saved: {dest.name}")
    return dest


# ---------------------------------------------------------------------------
# Avatar talking-head (ComfyUI InfiniteTalk)
# ---------------------------------------------------------------------------

def generate_avatar_clip(comfy: Comfy, avatar_name: str, audio_slice: Path,
                         beat_text: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  avatar cached: {dest.name}")
        return dest
    prompt = (f"older white male from California, gray hair, weathered face, "
              f"casual flannel shirt, {beat_text}, natural lighting, "
              f"shot on smartphone, slightly soft focus")
    print(f"  generating avatar clip: {beat_text[:50]}...")
    comfy.infinitetalk(
        avatar=avatar_name,
        audio=audio_slice,
        prompt=prompt,
        negative=NEGATIVE,
        w=AVATAR_W, h=AVATAR_H,
        frames=AVATAR_FRAMES,
        dest=dest,
        steps=10,
    )
    print(f"  saved: {dest.name}")
    return dest


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

def ken_burns(image_path: Path, dest: Path, duration: float):
    styles = [
        f"zoompan=z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='if(lte(zoom,1.0),1.3,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='min(zoom+0.001,1.2)':x='if(lte(on,1),0,x+1)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
        f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)+sin(on/30)*20':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}",
    ]
    vf = f"{random.choice(styles)},format=yuv420p"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def scale_clip(src: Path, dest: Path, duration: float):
    subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
               f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def assemble(segments: list[Path], voiceover: Path | None, out_dir: Path) -> Path:
    video_only = out_dir / "rv_video_only.mp4"
    listfile = out_dir / "concat_list.txt"
    listfile.write_text("".join(f"file '{s.resolve()}'\n" for s in segments))
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(video_only)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(f"Video assembled (no audio): {video_only}")

    if voiceover and voiceover.exists():
        final = out_dir / "rv_video_final.mp4"
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video_only), "-i", str(voiceover),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(final)
        ], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Final video: {final}")
            return final
        else:
            print(f"Audio merge failed (exit {result.returncode}).")
            if result.stderr:
                print(result.stderr[-500:])
            shutil.copy2(video_only, final)
            print(f"Copied video-only as: {final}")
            return final
    else:
        print("No voiceover found — video-only output.")
        return video_only


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="RV Living sample pipeline")
    ap.add_argument("--comfy-url", required=True,
                    help="RunPod ComfyUI proxy URL")
    ap.add_argument("--google-key", default=os.environ.get("GOOGLE_API_KEY", ""),
                    help="Google API key for Gemini TTS")
    ap.add_argument("--avatar", default="avatar.png",
                    help="Path to avatar image (uploaded to pod if local)")
    ap.add_argument("--script-file", default=None,
                    help="Custom script text file (default: built-in)")
    ap.add_argument("--assemble-only", action="store_true",
                    help="Skip generation, just assemble cached segments")
    ap.add_argument("--tts-only", action="store_true",
                    help="Only generate the voiceover")
    ap.add_argument("--image-duration", type=float, default=5.0,
                    help="Duration per image segment in seconds")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    segments_dir = OUT / "segments"
    segments_dir.mkdir(exist_ok=True)

    script = SCRIPT_DEFAULT
    if args.script_file:
        script = Path(args.script_file).read_text(encoding="utf-8")

    # --- Voiceover ---
    voiceover = None
    if args.google_key:
        voiceover = generate_voiceover(script, args.google_key, OUT)
    else:
        print("WARNING: No --google-key, skipping voiceover generation.")
        vo_path = OUT / "voiceover.wav"
        if vo_path.exists():
            voiceover = vo_path

    if args.tts_only:
        return

    # --- Generate segments ---
    comfy = Comfy(args.comfy_url) if not args.assemble_only else None

    avatar_path = Path(args.avatar)
    avatar_name = None
    if comfy and avatar_path.exists():
        print(f"Uploading avatar: {avatar_path}")
        up = comfy.upload(avatar_path)
        avatar_name = up["name"]
        print(f"Avatar uploaded as: {avatar_name}")

    # For avatar clips we need audio slices. Create a silent placeholder
    # if no voiceover, or slice the voiceover evenly for avatar beats.
    avatar_beat_indices = [i for i, b in enumerate(BEATS) if b["type"] == "avatar"]
    avatar_audio_slices = {}

    if voiceover and voiceover.exists() and not args.assemble_only:
        vo_dur = get_duration(voiceover)
        n_avatar = len(avatar_beat_indices)
        slice_dur = min(3.2, vo_dur / max(len(BEATS), 1))
        for idx, bi in enumerate(avatar_beat_indices):
            # Place avatar audio at roughly even intervals through the VO
            offset = (bi / max(len(BEATS) - 1, 1)) * max(0, vo_dur - slice_dur)
            slice_path = segments_dir / f"avatar_audio_{idx:02d}.wav"
            if not slice_path.exists() or slice_path.stat().st_size == 0:
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(voiceover),
                    "-ss", str(offset), "-t", str(slice_dur),
                    "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1",
                    str(slice_path)
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            avatar_audio_slices[bi] = slice_path

    segment_files = []
    for i, beat in enumerate(BEATS):
        seg_name = f"seg_{i:02d}"

        if beat["type"] == "image":
            img = segments_dir / f"{seg_name}.png"
            vid = segments_dir / f"{seg_name}.mp4"

            if vid.exists() and vid.stat().st_size > 0:
                print(f"[{seg_name}] skip (cached)")
                segment_files.append(vid)
                continue

            if args.assemble_only:
                if vid.exists():
                    segment_files.append(vid)
                continue

            generate_image(comfy, beat["prompt"], img, seed=i * 42 + 7)
            ken_burns(img, vid, args.image_duration)
            segment_files.append(vid)

        elif beat["type"] == "avatar":
            vid = segments_dir / f"{seg_name}_avatar.mp4"
            scaled = segments_dir / f"{seg_name}.mp4"

            if scaled.exists() and scaled.stat().st_size > 0:
                print(f"[{seg_name}] skip (cached)")
                segment_files.append(scaled)
                continue

            if args.assemble_only:
                if scaled.exists():
                    segment_files.append(scaled)
                continue

            if not avatar_name:
                print(f"[{seg_name}] SKIP — no avatar image")
                continue

            audio_slice = avatar_audio_slices.get(i)
            if not audio_slice:
                # create a short silent wav
                audio_slice = segments_dir / f"silent_{i:02d}.wav"
                if not audio_slice.exists():
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "lavfi", "-i",
                        "anullsrc=r=24000:cl=mono", "-t", "3",
                        "-c:a", "pcm_s16le", str(audio_slice)
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            generate_avatar_clip(comfy, avatar_name, audio_slice,
                                 beat["text"], vid)
            avatar_dur = AVATAR_FRAMES / AVATAR_FPS
            scale_clip(vid, scaled, avatar_dur)
            segment_files.append(scaled)

    if not segment_files:
        print("No segments found. Run without --assemble-only first.")
        return

    # --- Assemble ---
    print(f"\nAssembling {len(segment_files)} segments...")
    assemble(segment_files, voiceover, OUT)
    print("Done!")


if __name__ == "__main__":
    main()
