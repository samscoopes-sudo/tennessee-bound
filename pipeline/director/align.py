"""Snap shot timings to the real voiceover audio.

Word-count timing drifts whenever the narrator pauses or changes pace. This
transcribes the VO with word-level timestamps (faster-whisper), aligns the
transcript to the shot narration text (difflib, tolerant of transcription
errors since the VO is TTS of the same script), and rewrites each shot's
start/duration to the actual moment its words are spoken.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from . import config


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def transcribe(vo_path: Path, model_size: str = "small") -> list[tuple[str, float]]:
    """Return [(normalized_word, start_seconds), ...] across the whole VO."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(vo_path), word_timestamps=True, vad_filter=True)
    words: list[tuple[str, float]] = []
    for seg in segments:
        for w in (seg.words or []):
            nw = _norm(w.word)
            if nw:
                words.append((nw, float(w.start)))
    return words


def _interp(i: int, known: list[tuple[int, float]]) -> float:
    """Linear-interpolate a time for script-word index i from known anchors."""
    if i <= known[0][0]:
        return known[0][1]
    if i >= known[-1][0]:
        return known[-1][1]
    for (a_i, a_t), (b_i, b_t) in zip(known, known[1:]):
        if a_i <= i <= b_i:
            frac = (i - a_i) / (b_i - a_i) if b_i > a_i else 0.0
            return a_t + frac * (b_t - a_t)
    return known[-1][1]


def retime(shots: list[dict], trans: list[tuple[str, float]], total: float) -> int:
    """Rewrite start/duration on shots in place. Returns count of anchored words."""
    swords, owner = [], []
    for idx, s in enumerate(shots):
        for tok in s.get("narration", "").split():
            nt = _norm(tok)
            if nt:
                swords.append(nt)
                owner.append(idx)
    twords = [w for w, _ in trans]
    ttimes = [t for _, t in trans]

    stime: list[float | None] = [None] * len(swords)
    sm = SequenceMatcher(a=swords, b=twords, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                stime[i1 + k] = ttimes[j1 + k]

    known = [(i, t) for i, t in enumerate(stime) if t is not None]
    if not known:
        return 0
    for i in range(len(stime)):
        if stime[i] is None:
            stime[i] = _interp(i, known)
    for i in range(1, len(stime)):
        if stime[i] < stime[i - 1]:
            stime[i] = stime[i - 1]

    first_time: dict[int, float] = {}
    for i, idx in enumerate(owner):
        first_time.setdefault(idx, stime[i])

    starts, prev = [], 0.0
    for idx in range(len(shots)):
        st = max(first_time.get(idx, prev), prev)
        starts.append(st)
        prev = st
    for idx, s in enumerate(shots):
        end = starts[idx + 1] if idx + 1 < len(shots) else total
        s["start"] = round(starts[idx], 2)
        s["duration"] = round(max(0.4, end - starts[idx]), 2)
    return len(known)


def merge_talking_heads(shots: list[dict]) -> list[dict]:
    """Collapse consecutive talking-head shots into one continuous clip (no jump-cut
    between two separate InfiniteTalk renders of the same avatar). Clears stale
    asset/source so everything regenerates against the new indices."""
    out: list[dict] = []
    i, n = 0, len(shots)
    while i < n:
        s = dict(shots[i])
        s.pop("asset", None)
        s.pop("source", None)
        if s["kind"] == "talking_head":
            narr = [s.get("narration", "")]
            dur = s["duration"]
            j = i + 1
            while j < n and shots[j]["kind"] == "talking_head":
                narr.append(shots[j].get("narration", ""))
                dur += shots[j]["duration"]
                j += 1
            s["narration"] = " ".join(x for x in narr if x)
            s["duration"] = round(dur, 2)
            out.append(s)
            i = j
        else:
            out.append(s)
            i += 1
    for k, s in enumerate(out):
        s["index"] = k
    return out


def align_shotlist(shots_path: Path, vo_path: Path, model_size: str = "small") -> None:
    plan = json.loads(shots_path.read_text())
    total = float(plan.get("vo_duration") or 0) or None
    print(f"Transcribing {vo_path.name} with faster-whisper ({model_size}) ...", flush=True)
    trans = transcribe(vo_path, model_size)
    if total is None:
        total = trans[-1][1] + 3 if trans else 0.0
    print(f"  {len(trans)} words timestamped; aligning to {len(plan['shots'])} shots ...", flush=True)
    anchored = retime(plan["shots"], trans, total)
    before = len(plan["shots"])
    plan["shots"] = merge_talking_heads(plan["shots"])
    plan["count"] = len(plan["shots"])
    shots_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    print(f"Re-timed shot-list from audio ({anchored} words anchored); "
          f"merged {before - len(plan['shots'])} adjacent talking-head shots. Wrote {shots_path}")
