#!/bin/bash
# Resilient render supervisor. Re-runs the (resumable) generate stage until every
# shot of the requested kind has an asset, waiting for ComfyUI to come back after
# any OOM restart. Stops if it stalls (no progress for 3 passes) — that needs a
# manual ComfyUI restart on the pod.
#   bash _render.sh <channel> <slug> <comfy_url> <broll|avatar>
set -u
cd ~/ai-video-pipeline/director
CHANNEL="$1"; SLUG="$2"; POD="$3"; ONLY="$4"
SL="channels/$CHANNEL/runs/$SLUG/shot-list.json"

remaining() {
  .venv/bin/python - "$SL" "$ONLY" <<'PY'
import json, sys, pathlib
d = json.load(open(sys.argv[1])); only = sys.argv[2]
def match(s):
    return (s["kind"] == "talking_head") if only == "avatar" else (s["kind"] != "talking_head")
print(sum(1 for s in d["shots"] if match(s)
          and not (s.get("asset") and pathlib.Path(s["asset"]).exists())))
PY
}

prev=-1; stuck=0
for pass in $(seq 1 40); do
  for w in $(seq 1 60); do                                   # wait up to 5 min for ComfyUI
    [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$POD/")" = "200" ] && break
    sleep 5
  done
  echo "=== pass $pass ($CHANNEL/$ONLY) $(date '+%H:%M:%S') ==="
  .venv/bin/python run.py generate --channel "$CHANNEL" --run "$SLUG" --comfy "$POD" --only "$ONLY"
  rem=$(remaining)
  echo "=== pass $pass done; remaining $ONLY shots: $rem ==="
  [ "$rem" = "0" ] && { echo "ALL $ONLY SHOTS DONE"; break; }
  if [ "$rem" = "$prev" ]; then stuck=$((stuck + 1)); else stuck=0; fi
  prev=$rem
  [ "$stuck" -ge 3 ] && { echo "STALLED at $rem $ONLY shots — restart ComfyUI on the pod, then re-run"; break; }
  sleep 10
done
