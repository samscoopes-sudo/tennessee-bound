"""Step 4 - composite the EDL onto the avatar video with FFmpeg.

The director decided; here we render, deterministically. One `ffmpeg` call
builds a filter graph that:
  * keeps the avatar as the base layer (its audio is the spine),
  * overlays each b-roll cue full-frame for its [start, end] window
    (video clips play; stills get a Ken Burns push-in),
  * draws lower-thirds and stat pop-ins as timed text.

Hard cuts only - overlays simply switch on/off with `enable=between(t,a,b)`,
matching the reference style.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import config
from .models import Cue, CueType, EditDecisionList, Motion

W, H, FPS = config.OUTPUT_WIDTH, config.OUTPUT_HEIGHT, config.OUTPUT_FPS
_STAT_DEFAULT_LEN = 2.0  # seconds a stat pop-in stays up if end == start

# A font that ships broadly on Debian/the Docker image.
_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def _ken_burns(label_in: str, label_out: str, seconds: float, mode: Motion) -> str:
    """Scale a still to frame and apply a slow 105->110% push (or reverse)."""
    frames = max(int(seconds * FPS), 1)
    if mode == Motion.KEN_BURNS_OUT:
        z = "if(lte(zoom,1.0),1.10,max(1.001,zoom-0.0007))"
    else:  # push-in default
        z = "min(zoom+0.0007,1.10)"
    return (
        f"[{label_in}]scale={W*2}:-1,"
        f"zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
        f"setsar=1[{label_out}]"
    )


def _scale_clip(label_in: str, label_out: str) -> str:
    return (
        f"[{label_in}]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1[{label_out}]"
    )


def compose(edl: EditDecisionList, source_path: str, output_path: str) -> str:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")

    inputs: list[str] = ["-i", source_path]
    filters: list[str] = []
    idx = 1  # input 0 is the avatar

    # base: normalise the avatar to the output frame
    filters.append(
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,fps={FPS}[base]"
    )
    cur = "base"

    broll = sorted(edl.broll_cues(), key=lambda c: c.start)
    for n, cue in enumerate(broll):
        if not cue.asset_path or not Path(cue.asset_path).exists():
            continue
        dur = max(cue.end - cue.start, 0.1)

        if cue.asset_is_video:
            inputs += ["-stream_loop", "-1", "-t", f"{dur:.2f}", "-i", cue.asset_path]
            filters.append(_scale_clip(f"{idx}:v", f"ov{n}"))
        else:
            inputs += ["-loop", "1", "-t", f"{dur:.2f}", "-i", cue.asset_path]
            filters.append(_ken_burns(f"{idx}:v", f"ov{n}", dur, cue.motion))

        if cue.type == CueType.SPLIT_SCREEN:
            # avatar on the left third, asset filling the right two-thirds
            filters.append(
                f"[ov{n}]scale={int(W*2/3)}:{H}:force_original_aspect_ratio=increase,"
                f"crop={int(W*2/3)}:{H}[ovs{n}]"
            )
            filters.append(
                f"[{cur}][ovs{n}]overlay=x={int(W/3)}:y=0:"
                f"enable='between(t,{cue.start:.2f},{cue.end:.2f})'[v{n}]"
            )
        else:
            filters.append(
                f"[{cur}][ov{n}]overlay=0:0:"
                f"enable='between(t,{cue.start:.2f},{cue.end:.2f})'[v{n}]"
            )
        cur = f"v{n}"
        idx += 1

    # text overlays draw last, on top of everything
    for n, cue in enumerate(edl.cues):
        if cue.type not in (CueType.LOWER_THIRD, CueType.STAT) or not cue.text:
            continue
        end = cue.end if cue.end > cue.start else cue.start + _STAT_DEFAULT_LEN
        txt = _escape(cue.text)
        if cue.type == CueType.LOWER_THIRD:
            draw = (
                f"drawtext=fontfile={_FONT}:text='{txt}':"
                f"fontcolor=white:fontsize={int(H*0.045)}:"
                f"borderw=3:bordercolor=black@0.8:"
                f"x=(w-text_w)/2:y=h-h*0.14:"
                f"enable='between(t,{cue.start:.2f},{end:.2f})'"
            )
        else:  # STAT - big, centered-upper pop-in
            draw = (
                f"drawtext=fontfile={_FONT}:text='{txt}':"
                f"fontcolor=white:fontsize={int(H*0.09)}:"
                f"borderw=4:bordercolor=black@0.85:"
                f"x=(w-text_w)/2:y=h*0.22:"
                f"enable='between(t,{cue.start:.2f},{end:.2f})'"
            )
        filters.append(f"[{cur}]{draw}[t{n}]")
        cur = f"t{n}"

    filter_complex = ";".join(filters)
    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{cur}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path
