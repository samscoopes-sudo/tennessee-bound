"""Narration script writer: a topic/title -> a full, narration-ready script via Claude.

Output is "VidRush-clean": pure spoken narration — no titles, headers, timestamps,
stage directions, bullet points, or numbering; numbers and dates written as words.
Paragraphs are blank-line separated so the planner can split them into shots.
"""
from __future__ import annotations

from pathlib import Path

import anthropic

from . import config, keys

WPM = 135  # spoken-narration pace, for word-count targeting


def build_system(niche: str, persona: str, items_low: int = 10, items_high: int = 15,
                 minutes: int = 19, script_notes: str = "") -> str:
    words = int(minutes * WPM)
    extra = f"\n\nCHANNEL-SPECIFIC RULES (these override anything above if they conflict):\n{script_notes}" if script_notes else ""
    return f"""You write narration scripts for a faceless, documentary-style YouTube channel.
Genre: {niche}
Narrator: {persona}

Write ONE complete narration script for the given video topic/title.

LENGTH: about {words} words (~{minutes} minutes spoken). Stay within +/-150 words.
CONTENT: a countdown/list piece covering {items_low} to {items_high} concrete items (tips, tricks,
remedies, methods — whatever fits the topic). Develop each item as flowing spoken storytelling with a
specific, real detail: what it is, how it was done, and why it worked — never a bare list.

RETENTION ENGINEERING (this is the top priority — it is what keeps people from clicking away):

1. FIRST 30 SECONDS (the single most important part of the whole script). Follow VPC:
   - VALIDATE THE CLICK: in the first two or three sentences, concretely confirm the viewer is in the
     right place by delivering on the exact promise of the title — name the subject and restate the
     promise in vivid terms. Never make them wait to find out the video is what they came for.
   - PEAK CURIOSITY: right after, stack two or three curiosity teasers (open loops) about what is coming,
     including ONE big loop you will NOT pay off until near the very end ("there is one of these that
     saved more families than all the rest put together — I will get to it, so stay with me").

2. OPEN LOOPS (the core technique; the brain hates unfinished business — the Zeigarnik effect):
   - Build every intriguing beat as OPEN -> BUILD -> PAYOFF, drip-feeding the resolution. Introduce the
     intrigue WITHOUT resolving it immediately, build a little tension, then pay it off a beat or two later.
   - Do NOT front-load the answer. Instead of "the secret was buttermilk," write "and the one she guarded
     closest she never said out loud — you will see why in a moment," then reveal it shortly after.
   - Overlap loops: open the next one before you fully close the last, so an unresolved thread is always
     pulling the viewer forward. Use lines like "but that was not even the strangest one" and "we will
     come back to that."
   - CLOSE EVERY LOOP you open. A tease you never pay off makes the viewer feel cheated and destroys
     trust and retention. The big intro loop MUST be resolved before the sign-off.

3. PATTERN INTERRUPTS (break the rhythm every ~20-40 seconds so the script never turns to mush):
   - Predictability is boredom. Roughly every 150-250 words, SHIFT something at the language level: drop a
     short, punchy one-line sentence after a run of long ones; turn and ask the viewer a direct question;
     slip in a wry aside or a warm personal memory; change the emotional register (a beat of humor, then a
     somber one); or briefly reframe ("now here is where it gets strange..."). Never let the script settle
     into the same-shaped sentence, item after item.

4. Close with a warm, natural spoken sign-off inviting people to subscribe, in the narrator's own voice
   (no links, no "click the button below").

VOICE: conversational and warm, fully in the narrator's persona. It must sound natural read ALOUD, not
written. No filler — every sentence either informs or hooks.

ACCURACY (critical): every claim must be accurate and specific. Do NOT invent facts, names, or dates.
Where a folk claim is not reliably true, frame it honestly ("old-timers swore by it", "some say",
"there's no proof, but...") instead of asserting it as fact. Write ORIGINAL narration — never reproduce
an existing script.

FORMAT — VidRush-clean, strict:
- Output PURE narration only. No title, no headers, no section labels, no item numbers, no timestamps,
  no stage directions, no bullet points, no markdown, no formatting of any kind.
- Write all numbers and dates as spoken words ("nineteen forty-two", "three tablespoons"), never digits.
- Separate paragraphs with a single blank line; each paragraph is one spoken beat.
Return only the narration text.{extra}"""


def write_script(topic: str, dest: Path, *, niche: str, persona: str,
                 items_low: int = 10, items_high: int = 15, minutes: int = 19,
                 model: str | None = None, script_notes: str = "", guidance: str = "") -> Path:
    client = anthropic.Anthropic(api_key=keys.anthropic_key())
    system = build_system(niche, persona, items_low, items_high, minutes, script_notes)
    user = f"Video topic / title:\n{topic}\n\nWrite the full narration script now."
    if guidance:
        user += f"\n\n{guidance}"
    print(f"writing script (~{int(minutes * WPM)} words) for: {topic}", flush=True)
    with client.messages.stream(
        model=model or config.SCRIPT_MODEL,
        max_tokens=20000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        msg = stream.get_final_message()
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    if not text:
        raise RuntimeError("empty script from model")
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_text(text + "\n", encoding="utf-8")
    wc = len(text.split())
    print(f"wrote {dest} — {wc} words (~{wc / WPM:.1f} min spoken)")
    return Path(dest)
