"""Insert on-camera narrator (talking_head) moments. Item-aware by default: one at the
intro, one on EACH countdown item's "Number X" line (so the host announces each item, like
the reference creator), and one at the outro. Falls back to N evenly-spaced if you pass a
count or if no countdown is detected.

    python inject_avatars.py shot-list.json          # item-aware (intro + each Number X + outro)
    python inject_avatars.py shot-list.json 6         # force 6 evenly-spaced instead
Run AFTER `plan` and BEFORE `align`/`itemize`/`generate`.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from director import items

path = sys.argv[1] if len(sys.argv) > 1 else "shot-list.json"
force_n = int(sys.argv[2]) if len(sys.argv) > 2 else None

plan = json.loads(Path(path).read_text())
shots = plan["shots"]
n = len(shots)

if force_n:                                        # legacy: N evenly-spaced
    mids = force_n - 2
    idxs = [0] + [round(n * (k + 1) / (mids + 1)) for k in range(mids)] + [n - 1]
    idxs = sorted(set(min(i, n - 1) for i in idxs))
else:
    countdown_idxs = set()
    for label, seg in items.segment(shots):
        if label.startswith("number"):
            countdown_idxs.add(seg[0]["index"])
    if countdown_idxs:                             # countdown: intro + each "Number X" + outro
        idxs = sorted({0, n - 1} | countdown_idxs)
    else:                                          # documentary: evenly-spaced (~10% of shots)
        count = max(3, round(n * 0.15))
        mids = count - 2
        idxs = [0] + [round(n * (k + 1) / (mids + 1)) for k in range(mids)] + [n - 1]
        idxs = sorted(set(min(i, n - 1) for i in idxs))

for i in idxs:
    s = shots[i]
    s["kind"] = "talking_head"
    s["prompt"] = ""
    s["motion"] = False
    for k in ("asset", "source", "flux_subject", "seed", "item"):
        s.pop(k, None)

Path(path).write_text(json.dumps(plan, indent=2, ensure_ascii=False))
th = sum(1 for s in shots if s["kind"] == "talking_head")
print(f"{n} shots -> {th} avatar moments at {idxs}")
