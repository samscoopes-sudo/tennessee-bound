"""Step 2 - the director.

Given the transcript and a style preset, ask Claude to produce an Edit
Decision List: what b-roll to show and when, where lower-thirds and stat
callouts go, following the house editing style. The LLM only *decides*; it
never touches pixels. Output is validated into typed models so the compositor
can execute it deterministically.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config
from .models import EditDecisionList, Transcript

_SYSTEM = """You are the editing "director" for an automated video tool. You \
receive a transcript (with timestamps) of a raw talking-head/avatar video and a \
STYLE PRESET describing the house editing style. You output an Edit Decision \
List (EDL) as JSON: the plan for what b-roll footage, lower-thirds, and stat \
callouts to lay over the video, and exactly when.

Follow the style preset faithfully. Key rules distilled from it:
- The video is b-roll heavy. Cover the avatar with b-roll for roughly the \
target ratio of the runtime, returning to the avatar as an anchor every 30-45s.
- Default b-roll clip length ~2.5s (calm ~3.5s, punchy ~2.0s). Hard cuts only.
- Every b-roll cue needs a concrete visual `query` describing footage a stock \
library (Storyblocks) could return - prefer real footage. Set `prefer_source` \
to "storyblocks" for real-world/action shots, "cheap_image_gen" only for \
custom/abstract stills that stock wouldn't have.
- Add a `lower_third` when a name, title, or list item is introduced.
- Add a `stat` cue (type "stat") whenever a specific number, price, %, or \
punchy keyword is spoken - set its `start` to that word's timestamp so it \
pops in on the word. Keep `text` short.
- Use `split_screen` occasionally when comparing two things.
- Do not cover the very first ~3s (opening avatar hook) or the final outro.

Output ONLY valid JSON matching this shape:
{"style_preset": str, "energy": "calm|balanced|punchy",
 "cues": [{"type": "broll|lower_third|stat|split_screen",
           "start": float, "end": float,
           "query": str|null, "prefer_source": str|null,
           "motion": "ken_burns_in|ken_burns_out|pan|none",
           "text": str|null}]}
No prose, no markdown fences."""


def load_preset(name: str = "default") -> dict:
    path = config.STYLE_PRESET_DIR / f"{name}.json"
    return json.loads(Path(path).read_text())


def _compact_transcript(t: Transcript) -> str:
    """A token-lean rendering: one line per segment with start-end, plus the
    word timings the director needs for stat placement."""
    lines = []
    for s in t.segments:
        wt = " ".join(f"{w.text}@{w.start:.1f}" for w in s.words)
        lines.append(f"[{s.start:.1f}-{s.end:.1f}] {s.text}\n  words: {wt}")
    return "\n".join(lines)


def direct(
    transcript: Transcript,
    preset_name: str = "default",
    energy: str = "balanced",
) -> EditDecisionList:
    preset = load_preset(preset_name)

    from anthropic import Anthropic

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    user = (
        f"STYLE PRESET:\n{json.dumps(preset, indent=2)}\n\n"
        f"Requested energy: {energy}\n"
        f"Video duration: {transcript.duration:.1f}s\n\n"
        f"TRANSCRIPT:\n{_compact_transcript(transcript)}"
    )

    resp = client.messages.create(
        model=config.DIRECTOR_MODEL,
        max_tokens=8000,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()

    data = json.loads(raw)
    data.setdefault("style_preset", preset_name)
    data.setdefault("energy", energy)
    edl = EditDecisionList.model_validate(data)

    # Clamp any cue that runs past the source, and drop zero-length b-roll.
    clean = []
    for c in edl.cues:
        c.start = max(0.0, min(c.start, transcript.duration))
        c.end = max(c.start, min(c.end, transcript.duration))
        clean.append(c)
    edl.cues = clean
    return edl
