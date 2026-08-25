"""Shot planner: script -> shot-list.json via Claude.

Each paragraph of the script becomes 1-3 shots. Claude decides talking-head vs
b-roll and writes the b-roll subject prompt; timing, the first-5-min motion rule,
and the locked style suffix are applied deterministically in code afterward.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from . import config, keys


class Shot(BaseModel):
    narration: str                      # the words spoken during this shot (for timing + captions)
    kind: Literal["talking_head", "broll"]
    motion: bool                        # b-roll only: True -> Wan clip, False -> Ken Burns still
    prompt: str                         # b-roll subject prompt (bare); "" for talking_head


class ShotList(BaseModel):
    shots: list[Shot]


# Per-channel framing (niche / narrator / scene style) is injected; these defaults
# reproduce the original Appalachia prompt so the no-channel path is unchanged.
_DEFAULT_NICHE = ("weathered rural APPALACHIAN mountain / homestead aesthetic — NOT Amish; ordinary "
                  "Appalachian country and mountain folk, farmers, old-timers")
_DEFAULT_PERSONA = ("an older man in VOICEOVER; he appears on camera only a handful of times, "
                    "inserted separately")
_DEFAULT_SCENE = ("a calm rustic Appalachian kitchen still-life — the item on a weathered wooden "
                  "table or wood stove, with mason jars or a window softly behind it")


def build_system(niche: str = "", persona: str = "", scene_style: str = "") -> str:
    """The planner system prompt, parameterized by channel. The technical rules
    (subject-matched b-roll, avoid hands/faces, motion) are channel-agnostic."""
    niche = niche or _DEFAULT_NICHE
    persona = persona or _DEFAULT_PERSONA
    scene = scene_style or _DEFAULT_SCENE
    return f"""You are a video director for a faceless documentary-style YouTube channel
({niche} — narrated by {persona}).

Break the narration paragraph you are given into a sequence of SHOTS, about one every
~{config.SHOT_SECONDS:.1f} seconds of speech (roughly 8-11 words each; the finished video cuts about
every 5 seconds). For each shot decide:

- kind: ALWAYS "broll". Do NOT use "talking_head" — every shot is b-roll; the on-camera narrator
  is inserted separately at a few fixed points, so you never choose it.
- prompt: a SHORT bare visual subject that LITERALLY SHOWS WHAT THIS SENTENCE IS ABOUT. This is the
  single most important rule. Find the specific food / ingredient / tool / object / place the sentence
  names and put THAT on screen. Examples of the principle (literal subject, never filler):
    * "salt cuts coffee's bitterness"  -> a tin coffee pot beside a small dish of salt
    * "the old egg peels clean"        -> a peeled hard-boiled egg on a plate beside its shell
    * "she sweetened it with honey"    -> a jar of honey with a wooden dipper
    * "season the cast iron"           -> a black cast iron skillet
  Do NOT fall back on generic filler when the sentence names a specific thing.
  Frame that subject as {scene}. The setting is the STYLE; the thing the sentence names is the
  CONTENT. Static and grounded, like a plain photo of that exact thing. Use a general scene ONLY when
  the narration is genuinely general (an intro or transition), never when it names something specific.
- motion: (a slow move is added later, to ~1 shot in 4) set true only for subjects that naturally
  move — steam, boiling or simmering water, a glowing fire, liquid being poured — else false.
  STRICTLY AVOID (never depict): people walking or in mid-motion, close-up hands doing detailed
  manipulation, complex human activity, and clear human faces — AI warps these badly.

Rules:
- Cover the whole paragraph; the narration fields concatenated should ~equal the paragraph.
- Every shot is b-roll (kind="broll").
- Never invent facts; only depict what the narration is about.
Return the shots in order."""


def read_paragraphs(script_path: Path) -> list[str]:
    text = script_path.read_text(encoding="utf-8")
    # strip any leading "N\t" line-number prefixes if present, then split on blank lines
    text = re.sub(r"(?m)^\s*\d+\t", "", text)
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def vo_duration_seconds(vo_path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(vo_path)],
        text=True,
    )
    return float(out.strip())


def _plan_paragraph(client: anthropic.Anthropic, topic: str, paragraph: str,
                    system: str, model: str) -> list[Shot]:
    for attempt in range(6):                       # retry transient overload/rate/server errors
        try:
            resp = client.messages.parse(
                model=model,
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": f"Video topic: {topic}\n\nParagraph:\n{paragraph}"}],
                output_format=ShotList,
            )
            plan = resp.parsed_output
            return plan.shots if plan else []
        except Exception as e:
            code = getattr(e, "status_code", None)
            if code in (408, 429, 500, 502, 503, 504, 529) and attempt < 5:
                wait = 3 * (attempt + 1)
                print(f"    (transient {code}, retry in {wait}s)", flush=True)
                time.sleep(wait)
                continue
            raise


def build_plan(script_path: Path, vo_path: Path, topic: str, *,
               niche: str = "", persona: str = "", scene_style: str = "",
               planner_model: str | None = None) -> dict:
    client = anthropic.Anthropic(api_key=keys.anthropic_key())
    total = vo_duration_seconds(vo_path)
    paragraphs = read_paragraphs(script_path)

    system = build_system(niche, persona, scene_style)
    model = planner_model or config.PLANNER_MODEL

    shots: list[Shot] = []
    for i, para in enumerate(paragraphs, 1):
        print(f"  planning paragraph {i}/{len(paragraphs)} ...", flush=True)
        shots.extend(_plan_paragraph(client, topic, para, system, model))

    # --- deterministic timing: distribute the real VO length by narration word count ---
    words = [max(1, len(s.narration.split())) for s in shots]
    total_words = sum(words)
    t = 0.0
    out_shots = []
    for s, w in zip(shots, words):
        dur = total * (w / total_words)
        if s.kind == "talking_head":
            dur = min(dur, config.TALKING_HEAD_MAX_SEC)

        # match the reference: every b-roll shot is smooth handheld motion, no stills
        motion = (s.kind == "broll") if config.ALL_BROLL_MOTION else s.motion
        prompt = config.styled(s.prompt) if s.kind == "broll" else ""

        out_shots.append({
            "index": len(out_shots),
            "start": round(t, 2),
            "duration": round(dur, 2),
            "kind": s.kind,
            "motion": bool(motion) if s.kind == "broll" else False,
            "narration": s.narration,
            "prompt": prompt,
            "negative": config.NEGATIVE if s.kind == "broll" else "",
        })
        t += dur

    return {
        "topic": topic,
        "vo_path": str(vo_path),
        "vo_duration": round(total, 2),
        "count": len(out_shots),
        "shots": out_shots,
    }


def write_plan(plan: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    th = sum(1 for s in plan["shots"] if s["kind"] == "talking_head")
    br = plan["count"] - th
    mo = sum(1 for s in plan["shots"] if s["motion"])
    print(f"\nWrote {out_path} — {plan['count']} shots "
          f"({th} talking-head, {br} b-roll; {mo} of them Wan motion), "
          f"covering {plan['vo_duration']:.0f}s.")
