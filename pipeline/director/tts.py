"""Voiceover generation: a script -> one VO file in the channel's cloned narrator
voice, via F5-TTS on the pod.

F5-TTS clones from a short reference clip (+its transcript) and speaks arbitrary
text, but quality drops on very long single generations and it caps the reference
at ~15s. So we split the script into modest chunks (by paragraph, sub-split long
paragraphs by sentence), synth each, and concatenate.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from .comfy import Comfy


def _paragraphs(text: str) -> list[str]:
    text = re.sub(r"(?m)^\s*\d+\t", "", text)          # strip any "N\t" line-number prefixes
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _split_long(paragraph: str, max_chars: int = 400) -> list[str]:
    if len(paragraph) <= max_chars:
        return [paragraph]
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", paragraph):
        if cur and len(cur) + len(sent) + 1 > max_chars:
            out.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        out.append(cur)
    return out


def chunks(text: str, max_chars: int = 400) -> list[str]:
    cs: list[str] = []
    for p in _paragraphs(text):
        cs.extend(_split_long(p, max_chars))
    return cs


def _concat(parts: list[Path], dest: Path) -> None:
    """Normalize every part to 24kHz mono wav, then concat (robust to mixed formats)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        norm = []
        for i, p in enumerate(parts):
            w = Path(td) / f"n{i:05d}.wav"
            subprocess.run(["ffmpeg", "-y", "-i", str(p), "-ar", "24000", "-ac", "1",
                            "-c:a", "pcm_s16le", str(w)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            norm.append(w)
        listfile = Path(td) / "list.txt"
        listfile.write_text("".join(f"file '{w}'\n" for w in norm))
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                        "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1", str(dest)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def synthesize(comfy_url: str, script_path: Path, ref_audio: Path, ref_text: str,
               dest: Path, work_dir: Path, *, seed: int = 1, speed: float = 1.0,
               max_chars: int = 400, nfe: int = 64, cfg: float = 2.0,
               cross_fade: float = 0.15, sway: float = -1.0) -> Path:
    """script -> dest VO (cloned voice). Resumable: skips chunks already rendered."""
    comfy = Comfy(comfy_url)
    cs = chunks(Path(script_path).read_text(encoding="utf-8"), max_chars)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"voiceover: {len(cs)} chunks via F5-TTS (cloning {Path(ref_audio).name})", flush=True)

    parts, made = [], 0
    for i, c in enumerate(cs):
        part = work_dir / f"vo_part_{i:04d}.wav"
        if part.exists() and part.stat().st_size > 0:
            parts.append(part)
            continue
        try:
            comfy.tts(c, ref_audio, ref_text, part, seed=seed, speed=speed,
                      nfe=nfe, cfg=cfg, cross_fade=cross_fade, sway=sway)
            parts.append(part)
            made += 1
            print(f"  [{i+1:>3}/{len(cs)}] {len(c):>3} chars -> {part.name}", flush=True)
        except Exception as e:
            print(f"  [{i+1:>3}/{len(cs)}] FAILED: {e}", flush=True)

    if not parts:
        raise RuntimeError("no VO parts produced — check the F5-TTS workflow/nodes")
    _concat(parts, Path(dest))
    print(f"\nWrote VO ({made} new chunks): {dest}")
    return Path(dest)
