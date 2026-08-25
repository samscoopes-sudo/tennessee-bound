"""Item-consistent b-roll for countdown videos + varied b-roll for documentaries.

For countdown scripts ("Number ten is... Number nine is..."), groups shots into items and
gives each item ONE canonical object so the SAME item appears throughout its segment.

For documentary/narrative scripts (no countdown), each shot gets its OWN unique visual
based on what its narration line describes — engine bays, interiors, driving shots, etc.

Run AFTER plan/inject_avatars/align, BEFORE generate. Writes each b-roll shot a `flux_subject`
(what to draw) and a `seed`; generate.py prefers those.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic
from pydantic import BaseModel

from . import config, keys

_WORDS = {"ten": 10, "nine": 9, "eight": 8, "seven": 7, "six": 6,
          "five": 5, "four": 4, "three": 3, "two": 2, "one": 1}
_NUM2W = {v: k for k, v in _WORDS.items()}
_START = re.compile(r"^\s*number\s+(ten|nine|eight|seven|six|five|four|three|two|one)\b", re.I)


def segment(shots: list[dict]) -> list[tuple[str, list[dict]]]:
    """[(label, [shots])] — 'intro' until the countdown starts, then one segment per item."""
    segments: list[tuple[str, list[dict]]] = []
    cur: list[dict] = []
    label = "intro"
    current: int | None = None
    expected: int | None = None
    for s in shots:
        start = False
        narr = s.get("narration", "")
        n = None
        m = _START.match(narr)
        if m:
            n = _WORDS[m.group(1).lower()]
        elif expected in _NUM2W and re.search(rf"\bnumber\s+{_NUM2W[expected]}\b", narr, re.I):
            n = expected
        if n is not None:
            if current is None:
                start, current, expected = True, n, n - 1
            elif n == expected:
                start, current, expected = True, n, n - 1
        if start:
            if cur:
                segments.append((label, cur))
            label = f"number {current}"
            cur = [s]
        else:
            cur.append(s)
    if cur:
        segments.append((label, cur))
    return segments


class ShotFrame(BaseModel):
    is_main: bool
    framing: str


class ItemVisual(BaseModel):
    object: str
    shots: list[ShotFrame]


class DocShotVisual(BaseModel):
    subject: str


class DocVisuals(BaseModel):
    shots: list[DocShotVisual]


def _is_countdown(shots: list[dict]) -> bool:
    for s in shots:
        if _START.match(s.get("narration", "")):
            return True
    return False


def _canon(client, model: str, label: str, scene_style: str, broll: list[dict]) -> ItemVisual:
    lines = "\n".join(f"[{i}] {s['narration']}" for i, s in enumerate(broll))
    system = (
        f'You design b-roll for one segment of a faceless countdown video. It must be CONSISTENT '
        f'(the SAME subject IN THE SAME SCENE throughout the segment) and visually VARIED (every shot is a '
        f'different camera angle of that scene). Segment: "{label}". Overall setting/style: {scene_style}.\n\n'
        f'Return:\n'
        f'- object: a detailed description of the ONE illustrative SCENE this segment is about — the main subject '
        f'shown IN THE SETTING AND ARRANGEMENT the narration describes, NOT the bare object floating alone. '
        f'Give exact colour, material, form, and the surrounding objects, so it can be redrawn the SAME way every time.\n'
        f'- shots: one entry per narration line, in order. Make each a DISTINCTLY DIFFERENT camera angle/distance '
        f'of THAT SAME scene. VARY distance and angle on every consecutive shot, but KEEP THE SAME SUBJECT.\n'
        f'    * is_main=true: the same scene from this shot\'s distinct angle (the DEFAULT).\n'
        f'    * is_main=false: ONLY for lines clearly about a DIFFERENT specific thing.\n'
        f'Never show people, hands, or text overlays. Return exactly {len(broll)} shot entries, in order.'
    )
    resp = client.messages.parse(model=model, max_tokens=4000, system=system,
                                 messages=[{"role": "user", "content": lines}],
                                 output_format=ItemVisual)
    return resp.parsed_output


def _doc_visuals(client, model: str, scene_style: str, broll: list[dict]) -> DocVisuals:
    lines = "\n".join(f"[{i}] {s['narration']}" for i, s in enumerate(broll))
    system = (
        f'You design b-roll for a faceless documentary video. Each shot must have its OWN UNIQUE '
        f'visual that LITERALLY ILLUSTRATES what its narration line describes. Overall style: {scene_style}.\n\n'
        f'For EACH shot, write a detailed `subject` — the specific scene/object/location that the narration line '
        f'is about, described in enough detail to generate a realistic photograph. Rules:\n\n'
        f'- VARIETY IS CRITICAL. Every shot must look DIFFERENT from its neighbors:\n'
        f'  * Vary the SUBJECT (different cars, different parts, different locations, different eras)\n'
        f'  * Vary the SETTING (garage interior, open road, showroom floor, race track, factory, auction house)\n'
        f'  * Vary the FRAMING (wide establishing, close-up detail, three-quarter, low angle, overhead)\n'
        f'  * Vary the LIGHTING (moody garage light, bright outdoor sun, dramatic spotlight, golden hour)\n'
        f'  * Vary the COLOR of the main subject where appropriate\n\n'
        f'- Match the narration LITERALLY:\n'
        f'  * "engine" lines -> show engine bays, carburetors, exhaust headers, valve covers\n'
        f'  * "racing" lines -> show a car on a race track, pit lane, checkered flags, trophies\n'
        f'  * "driving" lines -> show a car on an open road, highway, mountain pass\n'
        f'  * "interior" lines -> show dashboards, steering wheels, gauges, leather seats\n'
        f'  * "auction" or "value" lines -> show an auction podium, a car on display with a price placard\n'
        f'  * "factory" or "built" lines -> show an assembly line, factory floor\n'
        f'  * "design" or "style" lines -> show distinctive styling details (grille, badge, hood scoop)\n\n'
        f'- Be SPECIFIC: name exact colors, materials, decade-appropriate surroundings, specific car parts.\n'
        f'- NEVER show people, hands, faces, or text overlays.\n'
        f'- Return exactly {len(broll)} shot entries, in order.'
    )
    resp = client.messages.parse(model=model, max_tokens=8000, system=system,
                                 messages=[{"role": "user", "content": lines}],
                                 output_format=DocVisuals)
    return resp.parsed_output


def itemize(shots_path: Path, model: str | None = None, scene_style: str = "") -> dict:
    plan = json.loads(Path(shots_path).read_text())
    client = anthropic.Anthropic(api_key=keys.anthropic_key())
    model = model or config.PLANNER_MODEL
    broll_shots = [s for s in plan["shots"] if s["kind"] != "talking_head"]

    countdown = _is_countdown(plan["shots"])

    if countdown:
        segs = segment(plan["shots"])
        counts = {"items": 0, "shots": 0}
        seed = 5000
        for label, seg in segs:
            broll = [s for s in seg if s["kind"] != "talking_head"]
            if not broll:
                continue
            vis = _canon(client, model, label, scene_style, broll)
            obj = vis.object.strip().rstrip(".")
            frames = vis.shots
            for k, s in enumerate(broll):
                fr = frames[k] if k < len(frames) else ShotFrame(is_main=True, framing="on a weathered workbench")
                framing = fr.framing.strip().rstrip(".")
                s["flux_subject"] = f"{obj}, {framing}" if fr.is_main else framing
                s["seed"] = seed
                seed += 1
                s["item"] = label
                counts["shots"] += 1
            counts["items"] += 1
            print(f"  {label:>11}: {len(broll)} shots  <- {obj[:70]}", flush=True)
        print(f"\nitemized {counts['items']} segments / {counts['shots']} b-roll shots (countdown mode)")
    else:
        print("  documentary mode: each shot gets its own unique visual", flush=True)
        seed = 5000
        total = 0
        batch_size = 20
        for start in range(0, len(broll_shots), batch_size):
            batch = broll_shots[start:start + batch_size]
            vis = _doc_visuals(client, model, scene_style, batch)
            for k, s in enumerate(batch):
                subj = vis.shots[k].subject.strip().rstrip(".") if k < len(vis.shots) else s["prompt"]
                s["flux_subject"] = subj
                s["seed"] = seed
                seed += 1
                total += 1
            batch_end = start + len(batch)
            print(f"  shots {start+1}-{batch_end}: done", flush=True)
        print(f"\nitemized {total} b-roll shots (documentary mode — each shot unique)")

    Path(shots_path).write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return plan
