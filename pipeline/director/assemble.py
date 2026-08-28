"""ffmpeg assembly: shot assets + VO -> rough_cut.mp4.

Stills get a slow Ken Burns push-in; generated videos are scaled/padded to 16:9;
all clips are concatenated and the full voiceover is muxed on top as the spine.

Avatar shots cycle through 3 full-screen styles for variety:
  0 = medium (default full-frame)
  1 = close-up (crop + zoom into upper portion)
  2 = Ken Burns push-in on the avatar video
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from . import config

OUT_W, OUT_H = 1920, 1080
W, H, FPS = OUT_W, OUT_H, config.FPS

AVATAR_STYLES = ("medium", "closeup", "kenburns")


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


KB_EFFECTS = ("zoom_in", "zoom_out", "tl_br", "br_tl", "tc_bc", "bl_tr")


def _kenburns(image: Path, dur: float, dest: Path, effect: str = "zoom_in") -> None:
    """Smooth Ken Burns: zoom in/out or keyframe position moves (corner to corner)."""
    frames = max(1, int(dur * FPS))
    zi, zo = 1.0, 1.10
    rate = (zo - zi) / max(frames - 1, 1)
    if effect == "zoom_out":
        z = f"max({zo}-{rate:.6f}*on,{zi})"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif effect == "tl_br":
        z = "1.15"
        x = f"(iw-iw/zoom)*on/{frames}"
        y = f"(ih-ih/zoom)*on/{frames}"
    elif effect == "br_tl":
        z = "1.15"
        x = f"(iw-iw/zoom)*(1-on/{frames})"
        y = f"(ih-ih/zoom)*(1-on/{frames})"
    elif effect == "tc_bc":
        z = "1.15"
        x = "iw/2-(iw/zoom/2)"
        y = f"(ih-ih/zoom)*on/{frames}"
    elif effect == "bl_tr":
        z = "1.15"
        x = f"(iw-iw/zoom)*on/{frames}"
        y = f"(ih-ih/zoom)*(1-on/{frames})"
    else:
        z = f"min({zi}+{rate:.6f}*on,{zo})"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    vf = (f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    _run(["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", f"{dur:.3f}",
          "-vf", vf, "-an", str(dest)])


def _normalize_video(src: Path, dur: float, dest: Path) -> None:
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-i", str(src), "-t", f"{dur:.3f}", "-vf", vf,
          "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an", str(dest)])


def _avatar_medium(src: Path, dur: float, dest: Path) -> None:
    """Full-frame avatar, scaled to output."""
    _normalize_video(src, dur, dest)


def _avatar_closeup(src: Path, dur: float, dest: Path) -> None:
    """Crop to the upper 60% (head & shoulders) and scale up to fill the frame."""
    vf = (f"crop=iw:ih*0.6:0:0,"
          f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-i", str(src), "-t", f"{dur:.3f}", "-vf", vf, "-an", str(dest)])


def _avatar_kenburns(src: Path, dur: float, dest: Path) -> None:
    """Slow push-in on the avatar video for a cinematic feel."""
    frames = max(1, int(dur * FPS))
    zi, zo = 1.0, 1.08
    rate = (zo - zi) / max(frames - 1, 1)
    vf = (f"scale={W*2}:{H*2},"
          f"zoompan=z='min({zi}+{rate:.6f}*on,{zo})':"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={frames}:s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    _run(["ffmpeg", "-y", "-i", str(src), "-t", f"{dur:.3f}", "-vf", vf, "-an", str(dest)])


def _avatar_pip(src: Path, dur: float, dest: Path, bg: Path | None) -> None:
    """Small avatar in bottom-right corner over the previous b-roll (or black if none)."""
    if bg and bg.exists():
        # b-roll background, avatar overlay at 30% width in bottom-right
        aw = int(W * 0.30)
        ah = int(H * 0.30)
        margin = 40
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}[bg];"
              f"[1:v]scale={aw}:{ah}:force_original_aspect_ratio=decrease,"
              f"pad={aw}:{ah}:(ow-iw)/2:(oh-ih)/2[av];"
              f"[bg][av]overlay={W - aw - margin}:{H - ah - margin},"
              f"format=yuv420p")
        _run(["ffmpeg", "-y", "-i", str(bg), "-i", str(src), "-t", f"{dur:.3f}",
              "-filter_complex", vf, "-an", str(dest)])
    else:
        _avatar_medium(src, dur, dest)


def _avatar_split(src: Path, dur: float, dest: Path, bg: Path | None) -> None:
    """Avatar on the left half, b-roll on the right half (or black if none)."""
    hw = W // 2
    if bg and bg.exists():
        vf = (f"[1:v]scale={hw}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={hw}:{H}:(ow-iw)/2:(oh-ih)/2[av];"
              f"[0:v]scale={hw}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={hw}:{H}:(ow-iw)/2:(oh-ih)/2[br];"
              f"[av][br]hstack,fps={FPS},format=yuv420p")
        _run(["ffmpeg", "-y", "-i", str(bg), "-i", str(src), "-t", f"{dur:.3f}",
              "-filter_complex", vf, "-an", str(dest)])
    else:
        _avatar_medium(src, dur, dest)


def _vo_slice(vo: Path, start: float, dur: float, dest: Path) -> None:
    _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(vo),
          "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(dest)])


def _clip_audio(src: Path, dur: float, dest: Path) -> None:
    _run(["ffmpeg", "-y", "-i", str(src), "-t", f"{dur:.3f}", "-vn",
          "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(dest)])


def _find_nearby_broll(shots: list[dict], current_idx: int) -> Path | None:
    """Find the nearest b-roll asset before this avatar shot, for PiP/split background."""
    for s in reversed(shots):
        if s["index"] >= current_idx:
            continue
        if s["kind"] == "broll" and s.get("asset"):
            p = Path(s["asset"])
            if p.exists():
                return p
    return None


def assemble(shots_path: Path, vo_path: Path, out_path: Path) -> None:
    plan = json.loads(shots_path.read_text())
    shots = [s for s in plan["shots"] if s.get("asset")]
    if not shots:
        raise RuntimeError("No shots have an 'asset' — run `generate` first (or add paths by hand).")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    th_count = 0  # tracks which avatar shot we're on for style cycling

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        clips: list[Path] = []
        apieces: list[Path] = []
        for s in shots:
            asset = Path(s["asset"])
            i = s["index"]
            dur = float(s["duration"])
            clip = tmp / f"clip_{i:04d}.mp4"
            apiece = tmp / f"a_{i:04d}.wav"
            if s["kind"] == "talking_head":
                style = AVATAR_STYLES[th_count % len(AVATAR_STYLES)]
                if style == "closeup":
                    _avatar_closeup(asset, dur, clip)
                elif style == "kenburns":
                    _avatar_kenburns(asset, dur, clip)
                else:
                    _avatar_medium(asset, dur, clip)
                _clip_audio(asset, dur, apiece)
                th_count += 1
                print(f"  clip {i:>3}  {dur:5.1f}s  talking_head [{style}]", flush=True)
            else:
                is_image = asset.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".webp")
                if is_image:
                    _kenburns(asset, dur, clip, KB_EFFECTS[i % len(KB_EFFECTS)])
                else:
                    _normalize_video(asset, dur, clip)
                _vo_slice(vo_path, s["start"], dur, apiece)
                print(f"  clip {i:>3}  {dur:5.1f}s  {s['kind']}", flush=True)
            clips.append(clip)
            apieces.append(apiece)

        vlist = tmp / "v.txt"
        vlist.write_text("".join(f"file '{c}'\n" for c in clips))
        silent = tmp / "silent.mp4"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(vlist),
              "-c", "copy", str(silent)])

        alist = tmp / "a.txt"
        alist.write_text("".join(f"file '{a}'\n" for a in apieces))
        full_audio = tmp / "audio.wav"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alist),
              "-c", "copy", str(full_audio)])

        _run(["ffmpeg", "-y", "-i", str(silent), "-i", str(full_audio),
              "-map", "0:v", "-map", "1:a",
              "-c:v", "copy",
              "-c:a", "aac", "-b:a", "192k",
              str(out_path)])
    print(f"\nWrote {out_path}")
