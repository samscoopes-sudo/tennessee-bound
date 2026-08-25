"""Voiceover via ElevenLabs TTS.

The clone lives in the user's ElevenLabs account (a `voice_id`); we just call the
TTS API with that id. `clone_instant()` can create an Instant Voice Clone from a
reference recording via the API. For top quality, create a Professional Voice Clone
in the ElevenLabs dashboard instead and paste its voice_id into the channel config.

Auth: set ELEVENLABS_API_KEY in your environment. We never store or print the key.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .tts import _concat

API = "https://api.elevenlabs.io/v1"


def _sentences(text: str) -> list[str]:
    text = re.sub(r"(?m)^\s*\d+\t", "", text)              # strip "N\t" line-number prefixes
    out = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        for s in re.split(r"(?<=[.!?])\s+", para):
            s = s.strip()
            if s:
                out.append(s)
    return out


def _pack(text: str, max_chars: int) -> list[str]:
    """Greedily pack whole sentences into <= max_chars chunks (few large chunks).
    v3 is unstable on short snippets, so we want long requests, not sentence-sized ones."""
    out, cur = [], ""
    for s in _sentences(text):
        if cur and len(cur) + len(s) + 1 > max_chars:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def _v3_stability(v: float) -> float:
    return min((0.0, 0.5, 1.0), key=lambda x: abs(x - v))   # v3 accepts only Creative/Natural/Robust


def _key() -> str:
    k = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_API_KEY")
    if not k:                                   # fallback: a plain key file (no shell sourcing needed)
        for p in (Path.home() / ".elevenlabs_key",
                  Path(__file__).resolve().parent.parent / ".eleven_key"):
            if p.exists() and p.read_text().strip():
                k = p.read_text().strip()
                break
    if not k:
        raise SystemExit("no ElevenLabs key found: set ELEVENLABS_API_KEY, or put the key in "
                         "~/.elevenlabs_key")
    return k


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=None, raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def clone_instant(name: str, audio_paths: list[Path], *, remove_noise: bool = True,
                  labels: dict | None = None) -> str:
    """Create an Instant Voice Clone from one or more audio files; returns voice_id."""
    handles = [open(p, "rb") for p in audio_paths]
    files = [("files", (Path(p).name, h, "audio/mpeg")) for p, h in zip(audio_paths, handles)]
    data = {"name": name, "remove_background_noise": str(remove_noise).lower()}
    if labels:
        data["labels"] = json.dumps(labels)
    try:
        r = _session().post(f"{API}/voices/add", headers={"xi-api-key": _key()},
                            data=data, files=files, timeout=300)
    finally:
        for h in handles:
            h.close()
    if r.status_code >= 400:
        raise RuntimeError(f"voice clone failed ({r.status_code}): {r.text[:500]}")
    return r.json()["voice_id"]


def list_voices() -> list[dict]:
    r = _session().get(f"{API}/voices", headers={"xi-api-key": _key()}, timeout=60)
    r.raise_for_status()
    return [{"voice_id": v["voice_id"], "name": v.get("name")} for v in r.json().get("voices", [])]


def _tts_chunk(session, voice_id, text, model_id, settings, prev, nxt) -> bytes:
    body = {"text": text, "model_id": model_id, "voice_settings": settings}
    if prev:
        body["previous_text"] = prev           # request stitching keeps prosody continuous (v2)
    if nxt:
        body["next_text"] = nxt
    r = session.post(f"{API}/text-to-speech/{voice_id}",
                     params={"output_format": "wav_24000"},
                     headers={"xi-api-key": _key(), "Content-Type": "application/json"},
                     json=body, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"TTS failed ({r.status_code}): {r.text[:400]}")
    return r.content


def synthesize(script_path: Path, dest: Path, work_dir: Path, *, voice_id: str,
               model_id: str = "eleven_v3", stability: float = 0.5,
               similarity_boost: float = 0.85, style: float = 0.0,
               use_speaker_boost: bool = True, max_chars: int = 2500) -> Path:
    """script -> dest VO via ElevenLabs. Resumable: skips chunks already rendered."""
    if not voice_id:
        raise SystemExit("channel voice has no elevenlabs voice_id — create a voice and set "
                         "voice_id in channels/<name>/channel.json")
    is_v3 = model_id == "eleven_v3"
    cs = _pack(Path(script_path).read_text(encoding="utf-8"), max_chars)
    if is_v3:                                   # v3: only stability, no v2 knobs, no stitching
        settings = {"stability": _v3_stability(stability)}
    else:
        settings = {"stability": stability, "similarity_boost": similarity_boost,
                    "style": style, "use_speaker_boost": use_speaker_boost}
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    session = _session()
    print(f"voiceover: {len(cs)} chunks via ElevenLabs ({model_id}, voice {voice_id}, "
          f"stability={settings['stability']})", flush=True)

    parts, made = [], 0
    for i, c in enumerate(cs):
        part = work_dir / f"vo_part_{i:04d}.wav"
        if part.exists() and part.stat().st_size > 0:
            parts.append(part)
            continue
        prev = None if is_v3 else (cs[i - 1] if i > 0 else None)
        nxt = None if is_v3 else (cs[i + 1] if i < len(cs) - 1 else None)
        audio = _tts_chunk(session, voice_id, c, model_id, settings, prev, nxt)
        part.write_bytes(audio)
        parts.append(part)
        made += 1
        print(f"  [{i + 1:>3}/{len(cs)}] {len(c):>4} chars -> {part.name}", flush=True)

    if not parts:
        raise RuntimeError("no VO parts produced")
    _concat(parts, Path(dest))
    print(f"\nWrote VO ({made} new chunks): {dest}")
    return Path(dest)
