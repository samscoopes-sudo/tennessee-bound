#!/usr/bin/env python3
"""Faceless Video Pipeline — simple web UI.

A no-terminal front end for the director. Start it, open the browser, fill in a
topic + your pod URL, click "Make Video", and watch the log. It runs the exact
same stages as the runbook (script -> voice -> plan -> avatars -> align ->
itemize -> cadence -> render broll -> render avatar -> assemble), but as one
click, and cross-platform (no bash needed, so it works on Windows).

Run it from inside the `pipeline/` folder, with the venv active:

    python webui.py

then open http://127.0.0.1:5000 in your browser.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

from director import channels as ch

HERE = Path(__file__).resolve().parent
PY = sys.executable  # the venv's python, so subprocesses use the same env

app = Flask(__name__)

# ---- one job at a time; keep its log + state in memory -----------------------
JOB = {"running": False, "log": [], "done": False, "ok": False, "video": None, "label": ""}
LOCK = threading.Lock()


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with LOCK:
        JOB["log"].append(line)
    print(line, flush=True)


def run_cmd(args: list[str], cwd: Path = HERE) -> int:
    """Run a subprocess, streaming its output into the job log. Returns exit code."""
    log("$ " + " ".join(str(a) for a in args))
    p = subprocess.Popen(args, cwd=str(cwd), stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in p.stdout:
        with LOCK:
            JOB["log"].append(line.rstrip("\n"))
    p.wait()
    if p.returncode != 0:
        log(f"!! step failed (exit {p.returncode})")
    return p.returncode


def remaining_shots(shotlist: Path, only: str) -> int:
    """How many shots of this kind still have no rendered asset (mirrors _render.sh)."""
    d = json.loads(shotlist.read_text())

    def match(s):
        return (s["kind"] == "talking_head") if only == "avatar" else (s["kind"] != "talking_head")

    return sum(1 for s in d["shots"] if match(s)
               and not (s.get("asset") and Path(HERE / s["asset"]).exists()
                        or s.get("asset") and Path(s["asset"]).exists()))


def render_pass(channel: str, slug: str, pod: str, only: str, limit: int | None) -> bool:
    """Resilient render: re-run `generate` until every shot of this kind is done."""
    shotlist = HERE / "channels" / channel / "runs" / ch.slugify(slug) / "shot-list.json"
    prev, stuck = -1, 0
    for attempt in range(1, 41):
        # wait up to 5 min for ComfyUI to answer
        import urllib.request
        for _ in range(60):
            try:
                urllib.request.urlopen(pod, timeout=10)
                break
            except Exception:
                time.sleep(5)
        log(f"=== render {only}: pass {attempt} ===")
        args = [PY, "run.py", "generate", "--channel", channel, "--run", slug,
                "--comfy", pod, "--only", only]
        if limit:
            args += ["--limit", str(limit)]
        run_cmd(args)
        rem = remaining_shots(shotlist, only)
        log(f"=== {only}: remaining {rem} shots ===")
        if rem == 0 or (limit and attempt >= 1):
            log(f"ALL {only} SHOTS DONE")
            return True
        stuck = stuck + 1 if rem == prev else 0
        prev = rem
        if stuck >= 3:
            log(f"STALLED at {rem} {only} shots — restart ComfyUI on the pod, then re-run.")
            return False
        time.sleep(10)
    return False


def pipeline(channel: str, topic: str, minutes: int, pod: str,
             script_text: str, limit: int | None) -> None:
    try:
        slug = ch.slugify(topic)
        rd = HERE / "channels" / channel / "runs" / slug
        (rd / "output").mkdir(parents=True, exist_ok=True)
        JOB["label"] = f"{channel} / {slug}"

        # 1. script — use pasted text if given, else write with Claude
        if script_text.strip():
            log("Using the script you provided (skipping Claude).")
            (rd / "script.txt").write_text(script_text.strip() + "\n", encoding="utf-8")
        else:
            if run_cmd([PY, "run.py", "script", "--channel", channel,
                        "--run", slug, "--topic", topic, "--minutes", str(minutes)]):
                return _fail()
        script_path = f"channels/{channel}/runs/{slug}/script.txt"

        # 2. voice — use a pre-placed vo.wav if present, else generate it
        if (rd / "vo.wav").exists():
            log("Found existing vo.wav — using it, skipping voice generation.")
        elif run_cmd([PY, "run.py", "voice", "--channel", channel, "--run", slug,
                      "--script", script_path, "--comfy", pod]):
            return _fail()
        # 3. plan
        if run_cmd([PY, "run.py", "plan", "--channel", channel, "--run", slug,
                    "--script", script_path]):
            return _fail()
        shotlist = f"channels/{channel}/runs/{slug}/shot-list.json"
        # 4. avatars
        if run_cmd([PY, "inject_avatars.py", shotlist]):
            return _fail()
        # 5. align
        if run_cmd([PY, "run.py", "align", "--channel", channel, "--run", slug]):
            return _fail()
        # 6. itemize (consistent scenes)
        code = (f"from director import items, channels; c=channels.load('{channel}'); "
                f"items.itemize('{shotlist}', scene_style=c.scene_style)")
        if run_cmd([PY, "-c", code]):
            return _fail()
        # 7. motion cadence
        if run_cmd([PY, "_reflag_motion.py", shotlist, "4"]):
            return _fail()

        # 8. render b-roll, then 9. render avatars
        if not render_pass(channel, slug, pod, "broll", limit):
            return _fail()
        if not render_pass(channel, slug, pod, "avatar", limit):
            return _fail()

        # 10. assemble
        if run_cmd([PY, "run.py", "assemble", "--channel", channel, "--run", slug]):
            return _fail()

        video = rd / "output" / "video.mp4"
        if video.exists():
            with LOCK:
                JOB["video"] = str(video)
            log(f"DONE — video ready: {video}")
            _finish(ok=True)
        else:
            log("Assembled, but video.mp4 not found — check the log above.")
            _fail()
    except Exception as e:
        log(f"!! unexpected error: {e}")
        _fail()


def _finish(ok: bool) -> None:
    with LOCK:
        JOB["running"] = False
        JOB["done"] = True
        JOB["ok"] = ok


def _fail() -> None:
    _finish(ok=False)


@app.route("/")
def index() -> str:
    opts = "".join(f"<option>{c}</option>" for c in ch.list_channels()) or "<option>(no channels yet)</option>"
    return PAGE.replace("__CHANNELS__", opts)


@app.route("/start", methods=["POST"])
def start():
    with LOCK:
        if JOB["running"]:
            return jsonify({"error": "A video is already being made."}), 409
        JOB.update({"running": True, "log": [], "done": False, "ok": False,
                    "video": None, "label": ""})
    d = request.json or {}
    limit = 6 if d.get("test") else None
    t = threading.Thread(target=pipeline, args=(
        d.get("channel", "").strip(), d.get("topic", "").strip(),
        int(d.get("minutes", 15) or 15), d.get("pod", "").strip(),
        d.get("script", ""), limit), daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/status")
def status():
    with LOCK:
        return jsonify({"running": JOB["running"], "done": JOB["done"], "ok": JOB["ok"],
                        "label": JOB["label"], "has_video": bool(JOB["video"]),
                        "log": "\n".join(JOB["log"][-400:])})


@app.route("/video")
def video():
    with LOCK:
        v = JOB["video"]
    if v and Path(v).exists():
        return send_file(v, mimetype="video/mp4")
    return "no video yet", 404


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>Faceless Video Maker</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
 body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#1a1a1a}
 h1{font-size:22px} label{display:block;margin:12px 0 4px;font-weight:600;font-size:14px}
 input,select,textarea{width:100%;padding:9px;border:1px solid #ccc;border-radius:8px;font-size:14px;box-sizing:border-box}
 textarea{min-height:120px;font-family:inherit}
 .row{display:flex;gap:12px}.row>div{flex:1}
 button{margin-top:16px;padding:12px 20px;background:#c0392b;color:#fff;border:0;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer}
 button:disabled{background:#aaa;cursor:not-allowed}
 .chk{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:14px}.chk input{width:auto}
 #log{white-space:pre-wrap;background:#0f1720;color:#c8e6c9;padding:14px;border-radius:8px;margin-top:16px;font-family:ui-monospace,Consolas,monospace;font-size:12.5px;height:340px;overflow:auto}
 .hint{color:#666;font-size:12.5px;margin-top:3px} video{width:100%;margin-top:16px;border-radius:8px}
 .status{margin-top:12px;font-weight:600}
</style></head><body>
<h1>🎬 Faceless Video Maker</h1>
<p class=hint>Fill this in, click <b>Make Video</b>, and watch the log. Keep your RunPod pod running while it renders, and stop it when you're done.</p>
<div class=row>
 <div><label>Channel</label><select id=channel>__CHANNELS__</select></div>
 <div><label>Length (minutes)</label><input id=minutes type=number value=5></div>
</div>
<label>Video topic / title</label>
<input id=topic placeholder="The Story of the Ford Shelby Mustang">
<label>Pod URL (from RunPod)</label>
<input id=pod placeholder="https://XXXXXXXX-8188.proxy.runpod.net">
<label>Script (optional — leave blank to auto-write with Claude)</label>
<textarea id=script placeholder="Paste a ready-made script here to skip the AI writing step..."></textarea>
<div class=chk><input type=checkbox id=test checked><label style="margin:0;font-weight:400">Test mode — render only the first few shots (fast &amp; cheap; uncheck for the full video)</label></div>
<button id=go onclick=start()>Make Video</button>
<div class=status id=statusline></div>
<div id=log></div>
<video id=player controls style=display:none></video>
<script>
let timer=null;
async function start(){
 const body={channel:channel.value,minutes:minutes.value,topic:topic.value,pod:pod.value,script:script.value,test:test.checked};
 if(!body.topic){alert("Please enter a topic.");return;}
 if(!body.pod && !test.checked){/* pod needed for render */}
 go.disabled=true;statusline.textContent="Starting…";player.style.display="none";
 const r=await fetch("/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 if(!r.ok){const e=await r.json();alert(e.error||"Could not start");go.disabled=false;return;}
 timer=setInterval(poll,2000);poll();
}
async function poll(){
 const r=await fetch("/status");const s=await r.json();
 log.textContent=s.log;log.scrollTop=log.scrollHeight;
 statusline.textContent=s.running?("Working… "+s.label):(s.done?(s.ok?"✅ Done!":"⚠️ Stopped — see log"):"");
 if(s.done){clearInterval(timer);go.disabled=false;
   if(s.has_video){player.src="/video?"+Date.now();player.style.display="block";}}
}
</script></body></html>"""

if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="127.0.0.1", port=5000, threaded=True)
