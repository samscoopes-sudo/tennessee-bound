"""Drive ComfyUI to produce every shot's asset, writing paths back into shot-list.json."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from . import config
from . import motion
from . import stock
from .comfy import Comfy

OUT = Path(__file__).resolve().parent.parent / "output"


def _slice_vo(vo: Path, start: float, dur: float, dest: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(vo),
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dest)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dest


def _make_still(comfy, s: dict, i: int, out: Path, style: str | None = None):
    """Realistic b-roll still on the pod: FLUX.1-dev + Boreal amateur-photo LoRA (FREE).
    Returns (path, source_tag)."""
    dest = out / f"br_{i:04d}.png"
    # itemized shots carry a full `flux_subject` (canonical object + framing) and a per-item seed
    # for cross-shot consistency; fall back to the bare planner subject otherwise.
    subject = s.get("flux_subject") or s["prompt"].split(",")[0].strip()
    prompt, lora, steps = config.flux_prompt(subject, style)
    st = comfy.flux_still(prompt, config.WAN22_W, config.WAN22_H, dest,
                          seed=int(s.get("seed", 1000 + i)),
                          lora=lora, guidance=config.FLUX_GUIDANCE, steps=steps)
    return st, "flux+boreal"


def generate(shots_path: Path, comfy_url: str, avatar: Path,
             limit: int | None = None, start: int = 0, force: bool = False,
             use_stock: bool = False, out_dir: Path | None = None,
             only: str | None = None, avatars: list[Path] | None = None,
             style: str | None = None) -> None:
    plan = json.loads(shots_path.read_text())
    vo = Path(plan["vo_path"])
    comfy = Comfy(comfy_url)
    out = Path(out_dir) if out_dir else OUT
    out.mkdir(parents=True, exist_ok=True)
    avatars = avatars or [avatar]                     # rotate narrator angles across avatar shots
    th_order = [s["index"] for s in plan["shots"] if s["kind"] == "talking_head"]

    stock_on = use_stock and stock.enabled()
    srcs = [n for n, e in (("Pexels", "PEXELS_API_KEY"), ("Pixabay", "PIXABAY_API_KEY"))
            if os.environ.get(e)]
    print(f"stock footage: {'ON (' + '+'.join(srcs) + ')' if stock_on else 'OFF -> all AI'}", flush=True)
    print("b-roll: stills = FLUX + Boreal (pod, free)  |  motion = Wan 2.1 14B (pod, free)", flush=True)

    considered = made = 0
    for s in plan["shots"]:
        if s["index"] < start:
            continue
        # render one model-set per pass: InfiniteTalk (avatar) never shares VRAM with FLUX/Wan
        if only == "broll" and s["kind"] == "talking_head":
            continue
        if only == "avatar" and s["kind"] != "talking_head":
            continue
        if limit and considered >= limit:
            break
        considered += 1
        i = s["index"]
        if not force and s.get("asset") and Path(s["asset"]).exists():
            print(f"  [{i:>3}] skip (have {Path(s['asset']).name})", flush=True)
            continue
        try:
            if s["kind"] == "talking_head":
                wav = _slice_vo(vo, s["start"], s["duration"], out / f"th_{i:04d}.wav")
                frames = max(config.FPS, int(round(s["duration"] * config.FPS)))
                av = avatars[th_order.index(i) % len(avatars)]   # rotate angles, resume-safe
                av = av if (av.exists() and av.stat().st_size > 0) else av.name
                asset = comfy.infinitetalk(av, wav, config.TALKING_HEAD_PROMPT,
                                           config.TALKING_HEAD_NEGATIVE,
                                           config.VIDEO_W, config.VIDEO_H, frames,
                                           out / f"th_{i:04d}.mp4")
            elif s["motion"]:
                asset = None
                if stock_on:
                    asset = stock.fetch(s["prompt"], s["duration"], out / f"br_{i:04d}_stock.mp4",
                                        want_w=config.STILL_W, want_h=config.STILL_H)
                if asset:
                    s["source"] = "stock"
                else:
                    still, stsrc = _make_still(comfy, s, i, out, style)   # FLUX+Boreal still
                    subject = s.get("flux_subject") or s["prompt"].split(",")[0]
                    cue = config.WAN22_MOTION_CUES[i % len(config.WAN22_MOTION_CUES)]
                    wan_prompt = f"{subject}. {cue}"
                    asset = comfy.wan_i2v(still, wan_prompt, config.wan_frames(s["duration"]),
                                          config.VIDEO_W, config.VIDEO_H, out / f"br_{i:04d}.mp4")
                    s["source"] = f"{stsrc}+wan21-14b"
            else:
                asset, s["source"] = _make_still(comfy, s, i, out, style)
            s["asset"] = str(asset)
            made += 1
            tag = s.get("source", "")
            print(f"  [{i:>3}] {s['kind']:<12} {tag:<5} -> {Path(asset).name}", flush=True)
            shots_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  [{i:>3}] FAILED: {e}", flush=True)

    shots_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    print(f"\nGenerated {made} new assets; paths written back to {shots_path}")
