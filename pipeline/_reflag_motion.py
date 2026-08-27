"""Re-flag b-roll shots to a fixed cadence: 4 Ken Burns STILLS, then 1 gentle Wan
MOTION clip, repeating (~80% stills, ~20% video). Preserves shot indices, timing,
and avatar shots. Reuses any already-rendered asset of the correct type; drops a
wrong-type asset so the shot re-renders (png for stills, mp4 for motion).

    python _reflag_motion.py channels/<ch>/runs/<slug>/shot-list.json [stride]
"""
import json
import sys
from pathlib import Path

sl = Path(sys.argv[1] if len(sys.argv) > 1 else "shot-list.json")
stride = int(sys.argv[2]) if len(sys.argv) > 2 else 5          # every 5th b-roll shot = motion (~80% stills, ~20% motion)
d = json.loads(sl.read_text())

i = mo = still = 0
for s in d["shots"]:
    if s["kind"] == "talking_head":
        continue
    motion = (i % stride == stride - 1)                        # 0,1,2,3 still -> 4 motion (~20%)
    i += 1
    s["motion"] = motion
    asset = s.get("asset", "")
    want_ext = ".mp4" if motion else ".png"
    if not asset.endswith(want_ext):                          # wrong type -> re-render
        s.pop("asset", None)
        s.pop("source", None)
    mo += motion
    still += not motion

sl.write_text(json.dumps(d, indent=2, ensure_ascii=False))
br = mo + still
print(f"b-roll {br}: {still} Ken Burns stills ({100*still/br:.0f}%) + {mo} Wan motion "
      f"({100*mo/br:.0f}%) — 1 motion every {stride}")
