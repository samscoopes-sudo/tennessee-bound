#!/usr/bin/env python3
"""2-minute Atlanta Georgia story video using Veo V2 for all clips.

No voiceover — uses text overlays on each clip.
Generates video clips via GenAIPro Veo, then assembles with ffmpeg text burns.

Usage:
  python3 test_atlanta_video.py --api-key <GENAIPRO_KEY>
  python3 test_atlanta_video.py --assemble-only
"""
import argparse, subprocess, time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from director.veo import Veo

OUT = Path("atlanta_output")
OUT.mkdir(exist_ok=True)

FPS = 24
VIDEO_W, VIDEO_H = 1280, 720

SCRIPT = [
    # --- INTRO (0:00 - 0:15) ---
    {
        "clip": "aerial cinematic drone shot of downtown Atlanta Georgia skyline at golden hour, skyscrapers, lush green trees, warm sunset light, photorealistic",
        "duration": 8,
        "text": "THE STORY OF ATLANTA",
        "subtext": "From Railroad Town to World City",
    },
    {
        "clip": "slow cinematic shot of a historic railroad crossing marker in rural Georgia, old wooden train tracks disappearing into forest, morning fog, golden light",
        "duration": 7,
        "text": "1837 — A railroad terminus",
        "subtext": "named 'Terminus' at the end of the Western & Atlantic line",
    },
    # --- CIVIL WAR (0:15 - 0:30) ---
    {
        "clip": "dramatic cinematic shot of a burning 1860s southern city at night, Civil War era buildings on fire, smoke rising, historical reconstruction style, film grain",
        "duration": 8,
        "text": "1864 — Sherman's March",
        "subtext": "Atlanta burned to the ground during the Civil War",
    },
    {
        "clip": "cinematic shot of rebuilding a southern American city in the 1870s, workers constructing brick buildings, horse-drawn carts on dirt roads, warm afternoon light",
        "duration": 7,
        "text": "From the ashes, a phoenix rose",
        "subtext": "Atlanta rebuilt itself stronger than before",
    },
    # --- CIVIL RIGHTS (0:30 - 0:50) ---
    {
        "clip": "cinematic slow motion shot of Ebenezer Baptist Church in Atlanta, red brick exterior, stained glass windows, warm sunlight, reverent atmosphere",
        "duration": 10,
        "text": "Birthplace of Dr. Martin Luther King Jr.",
        "subtext": "Atlanta became the cradle of the Civil Rights Movement",
    },
    {
        "clip": "cinematic wide shot of a peaceful 1960s civil rights march down a wide tree-lined Southern boulevard, diverse crowd walking together, golden afternoon light",
        "duration": 10,
        "text": "\"The city too busy to hate\"",
        "subtext": "Atlanta chose progress over division",
    },
    # --- MODERN GROWTH (0:50 - 1:15) ---
    {
        "clip": "cinematic drone flyover of Hartsfield-Jackson Atlanta International Airport, massive terminal complex, planes taxiing, scale and energy, blue sky",
        "duration": 8,
        "text": "World's busiest airport",
        "subtext": "Hartsfield-Jackson serves 100+ million passengers a year",
    },
    {
        "clip": "cinematic tracking shot through the CNN Center lobby in Atlanta, large screens showing news broadcasts, modern architecture, bustling people",
        "duration": 7,
        "text": "Media capital of the South",
        "subtext": "Home to CNN, Turner Broadcasting, and Tyler Perry Studios",
    },
    {
        "clip": "cinematic night shot of the Coca-Cola sign glowing in downtown Atlanta, neon lights reflecting on wet streets after rain, moody atmosphere",
        "duration": 5,
        "text": "Coca-Cola was born here",
        "subtext": "Invented in 1886 at a pharmacy on Peachtree Street",
    },
    {
        "clip": "cinematic aerial shot of the 1996 Olympic stadium in Atlanta with fireworks, grand celebration, massive crowds, patriotic atmosphere, night sky",
        "duration": 5,
        "text": "1996 — The Olympic Games",
        "subtext": "Atlanta welcomed the world",
    },
    # --- CULTURE (1:15 - 1:40) ---
    {
        "clip": "cinematic tracking shot through the Atlanta BeltLine trail at sunset, people walking and cycling, street art murals on concrete walls, warm golden light, urban park",
        "duration": 8,
        "text": "The BeltLine transformed the city",
        "subtext": "22 miles of trails connecting 45 neighborhoods",
    },
    {
        "clip": "cinematic close-up of southern comfort food — fried chicken, collard greens, mac and cheese, cornbread — on a rustic wooden table, steam rising, warm lighting",
        "duration": 7,
        "text": "Soul food capital",
        "subtext": "Where Southern tradition meets world-class cuisine",
    },
    {
        "clip": "cinematic wide shot of a live hip-hop concert stage in Atlanta at night, energetic crowd, colorful stage lights, smoke machines, dynamic energy",
        "duration": 5,
        "text": "Birthplace of trap music",
        "subtext": "OutKast, T.I., Future, Migos — Atlanta shaped hip-hop",
    },
    # --- OUTRO (1:40 - 2:00) ---
    {
        "clip": "cinematic golden hour timelapse of the Atlanta skyline from Piedmont Park, city reflecting in the lake, trees in foreground, clouds moving, peaceful",
        "duration": 10,
        "text": "Atlanta keeps rising",
        "subtext": "A city that always finds a way forward",
    },
    {
        "clip": "cinematic slow push-in on the Atlanta phoenix city seal carved in stone, dramatic lighting, shallow depth of field",
        "duration": 10,
        "text": "RESURGENS",
        "subtext": "\"Rising Again\" — the motto of Atlanta",
    },
]


def gen_clips(veo: Veo, out: Path) -> dict:
    clips = {}
    total = len(SCRIPT)
    credits = veo.credits()
    print(f"  Veo credits available: {credits}")
    if credits < total:
        print(f"  WARNING: need {total} credits but only have {credits}")

    for i, seg in enumerate(SCRIPT):
        key = f"clip_{i:04d}"
        dest = out / f"{key}.mp4"
        if dest.exists() and dest.stat().st_size > 0:
            clips[key] = dest
            print(f"  [{key}] skip (cached)")
            continue
        print(f"  [{key}] {seg['clip'][:60]}...")
        t0 = time.time()
        try:
            veo.text_to_video(seg["clip"], dest, duration=seg["duration"])
            clips[key] = dest
            print(f"  [{key}] OK {time.time()-t0:.1f}s")
        except Exception as e:
            print(f"  [{key}] FAILED: {e}")
    return clips


def burn_text_on_clip(src: Path, dest: Path, text: str, subtext: str,
                      duration: float):
    """Burn title + subtitle text onto a video clip."""
    # main title: large, centered, upper portion
    # subtitle: smaller, below title
    drawtext_main = (
        f"drawtext=text='{_esc(text)}'"
        f":fontsize=48:fontcolor=white:borderw=3:bordercolor=black"
        f":x=(w-text_w)/2:y=h*0.75"
        f":enable='between(t,0.5,{duration-0.5})'"
    )
    drawtext_sub = (
        f"drawtext=text='{_esc(subtext)}'"
        f":fontsize=28:fontcolor=white:borderw=2:bordercolor=black"
        f":x=(w-text_w)/2:y=h*0.75+60"
        f":enable='between(t,1.0,{duration-0.5})'"
    )
    vf = f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},{drawtext_main},{drawtext_sub}"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", str(dest)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _esc(s: str) -> str:
    """Escape text for ffmpeg drawtext filter."""
    return s.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:").replace("%", "\\%")


def assemble(clips: dict, out: Path) -> Path:
    """Burn text overlays and concat all clips."""
    burned = []
    for i, seg in enumerate(SCRIPT):
        key = f"clip_{i:04d}"
        if key not in clips:
            # black placeholder
            ph = out / f"placeholder_{i:04d}.mp4"
            if not ph.exists():
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi", "-i",
                    f"color=c=black:s={VIDEO_W}x{VIDEO_H}:r={FPS}:d={seg['duration']}",
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18",
                    str(ph)
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            src = ph
        else:
            src = clips[key]

        burned_clip = out / f"burned_{i:04d}.mp4"
        if not burned_clip.exists():
            print(f"  Burning text on clip {i:04d}...")
            burn_text_on_clip(src, burned_clip, seg["text"], seg["subtext"],
                              seg["duration"])
        burned.append(burned_clip)

    listfile = out / "clips_list.txt"
    listfile.write_text("".join(f"file '{c.resolve()}'\n" for c in burned))

    final = out / "atlanta_story.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        str(final)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"\n=== FINAL VIDEO: {final} ===")
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=None, help="GenAIPro API key")
    ap.add_argument("--assemble-only", action="store_true")
    ap.add_argument("--skip-gen", action="store_true", help="Skip video generation")
    args = ap.parse_args()

    total_dur = sum(s["duration"] for s in SCRIPT)
    print(f"Plan: {len(SCRIPT)} clips, ~{total_dur}s ({total_dur/60:.1f} min)")

    clips = {}
    if not args.assemble_only and not args.skip_gen:
        veo = Veo(args.api_key)
        print("\n=== GENERATING CLIPS ===")
        clips = gen_clips(veo, OUT)
    else:
        for i in range(len(SCRIPT)):
            p = OUT / f"clip_{i:04d}.mp4"
            if p.exists():
                clips[f"clip_{i:04d}"] = p

    print(f"\nAssets: {len(clips)}/{len(SCRIPT)} clips")
    print("\n=== ASSEMBLY ===")
    final = assemble(clips, OUT)
    print(f"Done! Final video: {final}")


if __name__ == "__main__":
    main()
