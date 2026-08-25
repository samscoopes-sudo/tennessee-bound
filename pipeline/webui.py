#!/usr/bin/env python3
"""Faceless Video Pipeline — web UI.

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
PY = sys.executable

app = Flask(__name__)

JOB = {"running": False, "log": [], "done": False, "ok": False, "video": None, "label": ""}
LOCK = threading.Lock()


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with LOCK:
        JOB["log"].append(line)
    print(line, flush=True)


def run_cmd(args: list[str], cwd: Path = HERE) -> int:
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
    d = json.loads(shotlist.read_text())

    def match(s):
        return (s["kind"] == "talking_head") if only == "avatar" else (s["kind"] != "talking_head")

    return sum(1 for s in d["shots"] if match(s)
               and not (s.get("asset") and Path(HERE / s["asset"]).exists()
                        or s.get("asset") and Path(s["asset"]).exists()))


def render_pass(channel: str, slug: str, pod: str, only: str, limit: int | None) -> bool:
    shotlist = HERE / "channels" / channel / "runs" / ch.slugify(slug) / "shot-list.json"
    prev, stuck = -1, 0
    for attempt in range(1, 41):
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
             script_text: str, limit: int | None, motion_pct: int) -> None:
    try:
        slug = ch.slugify(topic)
        rd = HERE / "channels" / channel / "runs" / slug
        (rd / "output").mkdir(parents=True, exist_ok=True)
        JOB["label"] = f"{channel} / {slug}"

        # 1. script
        if script_text.strip():
            log("Using the script you provided (skipping Claude).")
            (rd / "script.txt").write_text(script_text.strip() + "\n", encoding="utf-8")
        else:
            if run_cmd([PY, "run.py", "script", "--channel", channel,
                        "--run", slug, "--topic", topic, "--minutes", str(minutes)]):
                return _fail()
        script_path = f"channels/{channel}/runs/{slug}/script.txt"

        # 2. voice
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
        # 4. avatars (only if avatar image exists)
        avatar_path = HERE / "channels" / channel / "avatar.png"
        if avatar_path.exists():
            if run_cmd([PY, "inject_avatars.py", shotlist]):
                return _fail()
        else:
            log("No avatar.png found — skipping talking-head injection (100% b-roll).")
        # 5. align
        if run_cmd([PY, "run.py", "align", "--channel", channel, "--run", slug]):
            return _fail()
        # 6. itemize
        code = (f"from director import items, channels; c=channels.load('{channel}'); "
                f"items.itemize('{shotlist}', scene_style=c.scene_style)")
        if run_cmd([PY, "-c", code]):
            return _fail()
        # 7. motion cadence
        stride = max(1, round(100 / max(motion_pct, 10)))
        if run_cmd([PY, "_reflag_motion.py", shotlist, str(stride)]):
            return _fail()

        # 8. render b-roll
        if not render_pass(channel, slug, pod, "broll", limit):
            return _fail()
        # 9. render avatars (only if any talking_head shots exist)
        if avatar_path.exists():
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
    opts = "".join(f"<option>{c}</option>" for c in ch.list_channels())
    return PAGE.replace("__CHANNELS__", opts)


@app.route("/create_channel", methods=["POST"])
def create_channel():
    d = request.form
    name = ch.slugify(d.get("name", "").strip())
    if not name:
        return jsonify({"error": "Channel name is required."}), 400
    cdir = HERE / "channels" / name
    cdir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "title": d.get("name", name),
        "niche": d.get("niche", ""),
        "narrator_persona": d.get("narrator", ""),
        "scene_style": d.get("scene_style", ""),
        "avatar_count": 8,
    }
    (cdir / "channel.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    # save avatar if uploaded
    f = request.files.get("avatar")
    if f and f.filename:
        f.save(str(cdir / "avatar.png"))
    return jsonify({"ok": True, "channel": name})


@app.route("/start", methods=["POST"])
def start():
    with LOCK:
        if JOB["running"]:
            return jsonify({"error": "A video is already being made."}), 409
        JOB.update({"running": True, "log": [], "done": False, "ok": False,
                    "video": None, "label": ""})
    d = request.json or {}
    limit = 6 if d.get("test") else None
    motion_pct = int(d.get("motion", 50) or 50)
    t = threading.Thread(target=pipeline, args=(
        d.get("channel", "").strip(), d.get("topic", "").strip(),
        int(d.get("minutes", 5) or 5), d.get("pod", "").strip(),
        d.get("script", ""), limit, motion_pct), daemon=True)
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


PAGE = r"""<!doctype html><html><head><meta charset=utf-8>
<title>Faceless Video Maker</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0c0f14;color:#e0e0e0;min-height:100vh}
.wrap{max-width:900px;margin:0 auto;padding:24px 20px}
h1{font-size:26px;font-weight:700;margin-bottom:4px;color:#fff}
.sub{color:#888;font-size:13px;margin-bottom:20px}
.tabs{display:flex;gap:0;margin-bottom:20px;border-bottom:2px solid #1e2430}
.tab{padding:10px 20px;cursor:pointer;color:#888;font-weight:600;font-size:14px;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .2s}
.tab:hover{color:#ccc}.tab.active{color:#ff6b4a;border-bottom-color:#ff6b4a}
.panel{display:none}.panel.active{display:block}
label{display:block;margin:14px 0 5px;font-weight:600;font-size:13px;color:#aaa;text-transform:uppercase;letter-spacing:.5px}
input,select,textarea{width:100%;padding:10px 12px;background:#161b24;border:1px solid #2a3040;border-radius:8px;font-size:14px;color:#e0e0e0;font-family:inherit;outline:none;transition:border .2s}
input:focus,select:focus,textarea:focus{border-color:#ff6b4a}
textarea{min-height:110px;resize:vertical}
select{appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' fill='none' stroke='%23888' stroke-width='1.5'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center}
.row{display:flex;gap:12px}.row>div{flex:1}
.row3{display:flex;gap:12px}.row3>div{flex:1}
button{padding:12px 24px;background:#ff6b4a;color:#fff;border:0;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:background .2s;margin-top:16px}
button:hover{background:#e55a3a}button:disabled{background:#444;cursor:not-allowed;color:#888}
.btn-sec{background:#1e2430;color:#ccc;font-size:13px;padding:8px 16px;margin-top:10px}
.btn-sec:hover{background:#2a3040}
.chk{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:13px;color:#aaa}
.chk input{width:auto;accent-color:#ff6b4a}
#log{white-space:pre-wrap;background:#0a0e14;color:#80c080;padding:14px;border-radius:8px;margin-top:16px;font-family:'JetBrains Mono',ui-monospace,Consolas,monospace;font-size:12px;height:360px;overflow:auto;border:1px solid #1e2430;line-height:1.5}
.status{margin-top:14px;font-weight:600;font-size:14px;color:#ff6b4a}
video{width:100%;margin-top:16px;border-radius:8px;border:1px solid #1e2430}
.slider-row{display:flex;align-items:center;gap:12px}
.slider-row input[type=range]{flex:1;accent-color:#ff6b4a}
.slider-val{font-size:14px;font-weight:700;color:#ff6b4a;min-width:40px}
.hint{color:#666;font-size:11.5px;margin-top:3px}
.card{background:#161b24;border:1px solid #2a3040;border-radius:10px;padding:18px;margin-bottom:16px}
.card h3{font-size:15px;color:#fff;margin-bottom:12px}
.file-upload{border:2px dashed #2a3040;border-radius:8px;padding:20px;text-align:center;cursor:pointer;transition:border .2s;color:#666;font-size:13px}
.file-upload:hover{border-color:#ff6b4a;color:#aaa}
.file-upload input{display:none}
.file-upload img{max-width:120px;max-height:120px;border-radius:8px;margin-top:8px}
.success{color:#4ecdc4;font-weight:600}
</style></head><body>
<div class=wrap>
<h1>Faceless Video Maker</h1>
<p class=sub>AI-powered faceless YouTube videos — FLUX stills, Wan motion clips, InfiniteTalk avatars</p>
<div class=tabs>
 <div class="tab active" onclick="tab(this,'make')">Make Video</div>
 <div class=tab onclick="tab(this,'channel')">New Channel</div>
</div>

<!-- MAKE VIDEO PANEL -->
<div id=make class="panel active">
 <div class=row>
  <div><label>Channel</label><select id=channel><option value="">(select or create one)</option>__CHANNELS__</select></div>
  <div><label>Length (minutes)</label><input id=minutes type=number value=5 min=1 max=30></div>
 </div>
 <label>Video Topic / Title</label>
 <input id=topic placeholder="e.g. The Story of the Ford Shelby Mustang">
 <label>Pod URL (RunPod ComfyUI)</label>
 <input id=pod placeholder="https://XXXXXXXX-8188.proxy.runpod.net">
 <label>Script <span style="font-weight:400;text-transform:none;color:#666">(optional — leave blank to auto-write with Claude)</span></label>
 <textarea id=script placeholder="Paste a ready-made script here to skip the AI writing step..."></textarea>

 <div class=row>
  <div>
   <label>Motion B-Roll %</label>
   <div class=slider-row>
    <input type=range id=motion min=10 max=100 value=50 oninput="motionVal.textContent=this.value+'%'">
    <span class=slider-val id=motionVal>50%</span>
   </div>
   <p class=hint>Higher = more Wan video clips (slower render). Lower = more Ken Burns stills.</p>
  </div>
 </div>

 <div class=chk><input type=checkbox id=test><label style="margin:0;font-weight:400;text-transform:none;color:#aaa">Test mode — render only 6 shots (fast + cheap)</label></div>
 <button id=go onclick=start()>Make Video</button>
 <div class=status id=statusline></div>
 <div id=log></div>
 <video id=player controls style=display:none></video>
</div>

<!-- NEW CHANNEL PANEL -->
<div id=channel_panel class=panel>
 <div class=card>
  <h3>Create a New Channel</h3>
  <p class=hint style="margin-bottom:14px">Each channel has its own niche, narrator, visual style, and avatar. You can make unlimited videos per channel.</p>
  <label>Channel Name</label>
  <input id=ch_name placeholder="e.g. MotorLegends, AppalachianTales">
  <label>Niche / Topic Area</label>
  <textarea id=ch_niche rows=2 placeholder="e.g. Classic American muscle cars and their history — Ford, Chevy, Dodge"></textarea>
  <label>Narrator Persona</label>
  <input id=ch_narrator placeholder="e.g. A knowledgeable car enthusiast narrating in voiceover">
  <label>Scene Style (how b-roll looks)</label>
  <textarea id=ch_scene rows=2 placeholder="e.g. Professional car photography — showroom floors, open highways, close-up engine details, dramatic lighting"></textarea>
  <label>Avatar Image (narrator face for talking-head shots)</label>
  <div class=file-upload onclick="ch_avatar_input.click()">
   <input type=file id=ch_avatar_input accept="image/*" onchange="previewAvatar(this)">
   <div id=avatar_preview>Click to upload a face image (PNG/JPG)<br><span class=hint>Without this, the video will be 100% b-roll (no talking head)</span></div>
  </div>
  <button class=btn-sec onclick=createChannel()>Create Channel</button>
  <div id=ch_result></div>
 </div>
</div>
</div>

<script>
function tab(el,id){
 document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
 document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
 el.classList.add('active');
 document.getElementById(id==='channel'?'channel_panel':id).classList.add('active');
}
function previewAvatar(inp){
 if(inp.files&&inp.files[0]){
  const r=new FileReader();
  r.onload=e=>{avatar_preview.innerHTML='<img src="'+e.target.result+'">';};
  r.readAsDataURL(inp.files[0]);
 }
}
async function createChannel(){
 const fd=new FormData();
 fd.append('name',ch_name.value);
 fd.append('niche',ch_niche.value);
 fd.append('narrator',ch_narrator.value);
 fd.append('scene_style',ch_scene.value);
 if(ch_avatar_input.files[0]) fd.append('avatar',ch_avatar_input.files[0]);
 const r=await fetch('/create_channel',{method:'POST',body:fd});
 const d=await r.json();
 if(d.ok){
  ch_result.innerHTML='<p class=success>Channel "'+d.channel+'" created! Switch to Make Video tab.</p>';
  const o=document.createElement('option');o.value=d.channel;o.textContent=d.channel;
  channel.appendChild(o);channel.value=d.channel;
 } else {
  ch_result.innerHTML='<p style="color:#e55">'+d.error+'</p>';
 }
}
let timer=null;
async function start(){
 const body={channel:channel.value,minutes:minutes.value,topic:topic.value,pod:pod.value,
             script:script.value,test:test.checked,motion:motion.value};
 if(!body.channel){alert("Please select or create a channel first.");return;}
 if(!body.topic){alert("Please enter a topic.");return;}
 if(!body.pod){alert("Please enter your RunPod ComfyUI URL.");return;}
 go.disabled=true;statusline.textContent="Starting...";player.style.display="none";
 const r=await fetch("/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 if(!r.ok){const e=await r.json();alert(e.error||"Could not start");go.disabled=false;return;}
 timer=setInterval(poll,2000);poll();
}
async function poll(){
 const r=await fetch("/status");const s=await r.json();
 log.textContent=s.log;log.scrollTop=log.scrollHeight;
 statusline.textContent=s.running?("Working... "+s.label):(s.done?(s.ok?"Done!":"Stopped - see log"):"");
 if(s.done){clearInterval(timer);go.disabled=false;
   if(s.has_video){player.src="/video?"+Date.now();player.style.display="block";}}
}
</script></body></html>"""

if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="127.0.0.1", port=5000, threaded=True)
