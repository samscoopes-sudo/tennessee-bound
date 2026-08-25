"""Post-process an all-broll shot-list into the final structure, DETERMINISTICALLY.

- Motion: exactly 3 Ken-Burns stills : 1 Wan clip (every 4th b-roll shot is a clip).
- Avatar (talking_head): the intro, one more in the first minute, EVERY call-to-action
  beat (subscribe / like / bell / comment / channel ...), and the closing shot.
Then clears assets so `generate` rebuilds each shot in its correct form.

    python finalize_shots.py shot-list.json
"""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "shot-list.json"

# narration phrases that mean "this is a CTA" -> show the avatar
CTA = ("subscribe", "like this video", "hit the like", "hit that like", "smash the like",
       "leave a comment", "comment below", "let me know", "the bell", "notification",
       "share this", "this channel", "our channel", "thumbs up", "follow along",
       "hit subscribe", "don't forget to")

plan = json.loads(open(path).read())
shots = plan["shots"]
n = len(shots)

# --- choose avatar shots ---
avatar = {0, n - 1}                                   # intro + end
for s in shots:                                       # one more in the first minute (~30s in)
    if s["start"] >= 30:
        avatar.add(s["index"])
        break
for s in shots:                                       # every CTA beat
    if any(k in (s.get("narration") or "").lower() for k in CTA):
        avatar.add(s["index"])

# --- apply: avatars, then 3 stills : 1 clip across the remaining b-roll ---
broll_count = 0
for s in shots:
    if s["index"] in avatar:
        s["kind"] = "talking_head"
        s["prompt"] = ""
        s["motion"] = False
    else:
        s["kind"] = "broll"
        s["motion"] = (broll_count % 4 == 3)          # ...S S S V  S S S V...
        broll_count += 1
    s.pop("asset", None)
    s.pop("source", None)

open(path, "w").write(json.dumps(plan, indent=2, ensure_ascii=False))
th = sum(1 for s in shots if s["kind"] == "talking_head")
mo = sum(1 for s in shots if s["kind"] == "broll" and s["motion"])
still = sum(1 for s in shots if s["kind"] == "broll" and not s["motion"])
cta = th - min(3, th)  # rough: total avatars minus the fixed intro/mid/end
print(f"{n} shots -> {th} avatar (intro + minute-1 + {max(0, th-3)} CTA + end)")
print(f"b-roll: {still} stills (Ken Burns) + {mo} clips (Wan 2.2)  [3:1 pattern]")
print("stills are FREE; clips ~free on the pod")
