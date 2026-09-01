"""Assemble b-roll images into a silent video with Ken Burns effects.
Run on your PC:  python assemble_broll.py
Requires: ffmpeg installed and on PATH, plus the shot-list.json and broll/ folder.
"""
import json, subprocess, tempfile
from pathlib import Path

W, H, FPS = 1920, 1080, 25
SHOT_LIST = Path("channels/dave/runs/lawn-care-fall/shot-list.json")
BROLL_DIR = Path("channels/dave/runs/lawn-care-fall/output")
OUT = Path("channels/dave/runs/lawn-care-fall/output/video_broll.mp4")

KB_EFFECTS = ("zoom_in", "pan_ud", "pan_lr", "pan_du", "pan_rl")


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace")[-500:])


def kenburns(image, dur, dest, effect="zoom_in"):
    frames = max(1, int(dur * FPS))
    Z = "1.08"
    if effect == "pan_ud":
        z, x, y = Z, "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*on/{frames}"
    elif effect == "pan_du":
        z, x, y = Z, "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*(1-on/{frames})"
    elif effect == "pan_lr":
        z, x, y = Z, f"(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"
    elif effect == "pan_rl":
        z, x, y = Z, f"(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"
    else:
        zi, zo = 1.0, 1.04
        rate = (zo - zi) / max(frames - 1, 1)
        z = f"min({zi}+{rate:.6f}*on,{zo})"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    vf = (f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", f"{dur:.3f}",
         "-vf", vf, "-an", str(dest)])


def main():
    plan = json.loads(SHOT_LIST.read_text())
    shots = [s for s in plan["shots"] if s["kind"] == "broll"]

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        clips = []
        for s in shots:
            i = s["index"]
            dur = float(s["duration"])
            image = BROLL_DIR / f"br_{i:04d}.png"
            if not image.exists():
                print(f"  [{i:>3}] SKIP (no image)", flush=True)
                continue
            clip = tmp / f"clip_{i:04d}.mp4"
            effect = KB_EFFECTS[i % len(KB_EFFECTS)]
            if image.stat().st_size < 5000:
                print(f"  [{i:>3}] SKIP (too small {image.stat().st_size}B)", flush=True)
                continue
            print(f"  [{i:>3}] {dur:5.1f}s  {effect}", end="", flush=True)
            try:
                kenburns(image, dur, clip, effect)
                clips.append(clip)
                print("  OK", flush=True)
            except Exception as e:
                try:
                    run(["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", f"{dur:.3f}",
                         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                         "-r", str(FPS), "-an", str(clip)])
                    clips.append(clip)
                    print("  OK (fallback)", flush=True)
                except Exception:
                    print(f"  FAILED: {e}", flush=True)

        if not clips:
            print("No clips produced!")
            return

        vlist = tmp / "v.txt"
        vlist.write_text("".join(f"file '{c}'\n" for c in clips))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(vlist),
             "-c", "copy", str(OUT)])

    print(f"\nDone! {len(clips)} clips -> {OUT}")


if __name__ == "__main__":
    main()
