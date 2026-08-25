"""ComfyUI HTTP API client + thin per-workflow wrappers.

Transport (queue / poll / download / upload) runs through a retrying Session so
transient RunPod proxy resets don't kill a shot. PARAM_MAP maps each workflow's
injectable widgets (prompt, seed, dimensions, input image/audio, frame count) to
the real node ids read from the exported API-format JSONs in workflows/.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"

# Maps injectable params -> (node_id, widget_field) in each workflows/<name>.json.
PARAM_MAP: dict[str, dict] = {
    "qwen_still": {
        "file": "qwen_still.json",
        "prompt": ("238:227", "text"),      # CLIP Text Encode (Positive)
        "width": ("238:232", "width"),      # EmptySD3LatentImage
        "height": ("238:232", "height"),
        "seed": ("238:230", "seed"),        # KSampler
    },
    "infinitetalk": {
        "file": "infinitetalk.json",
        "image": ("284", "image"),          # LoadImage (avatar)
        "audio": ("125", "audio"),          # LoadAudio (voiceover slice)
        "prompt": ("241", "positive_prompt"),
        "negative": ("241", "negative_prompt"),
        "width": ("245", "value"),          # INTConstant "Width"
        "height": ("246", "value"),         # INTConstant "Height"
        "frames": ("270", "value"),         # INTConstant "Max frames" -> clip length
    },
    "wan_i2v": {
        "file": "wan_i2v.json",
        "image": ("58", "image"),           # LoadImage (the Qwen still)
        "prompt": ("16", "positive_prompt"),
        "width": ("68", "width"),           # Resize Image v2 -> also drives encode dims
        "height": ("68", "height"),
        "frames": ("63", "num_frames"),     # WanVideoImageToVideoEncode
    },
    "flux_still": {
        "file": "flux_still.json",
        "prompt": ("3", "text"),            # CLIP Text Encode (Positive)
        "width": ("6", "width"),            # EmptySD3LatentImage
        "height": ("6", "height"),
        "seed": ("7", "seed"),              # KSampler
        "lora": ("2", "strength_model"),    # Realism LoRA strength
        "guidance": ("5", "guidance"),      # FluxGuidance (lower = flatter, less "enhanced")
    },
    "wan22": {
        "file": "wan22.json",
        "image": ("56", "image"),           # LoadImage (the Nano Banana still)
        "prompt": ("6", "text"),            # CLIP Text Encode (positive)
        "width": ("55", "width"),           # Wan22ImageToVideoLatent
        "height": ("55", "height"),
        "length": ("55", "length"),
        "fps": ("57", "fps"),               # CreateVideo
        "seed": ("3", "seed"),              # KSampler
    },
    "tts": {                                 # F5-TTS voice cloning (ComfyUI-F5-TTS, FromModel node)
        "file": "tts.json",
        "ref_audio": ("1", "audio"),         # LoadAudio (narrator reference clip)
        "ref_text": ("2", "sample_text"),    # transcript of the reference clip
        "text": ("2", "speech"),             # text to speak (a script chunk)
        "seed": ("2", "seed"),
        "speed": ("2", "speed"),
        "nfe": ("2", "nfe_step"),            # denoising steps (higher = smoother)
        "cfg": ("2", "cfg_strength"),        # guidance (higher = tighter to one speaker)
        "cross_fade": ("2", "cross_fade_duration"),
        "sway": ("2", "sway_sampling_coef"),
    },
}


class Comfy:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.client_id = uuid.uuid4().hex
        self.session = requests.Session()
        retry = Retry(total=6, connect=6, read=6, backoff_factor=1.5,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=None, raise_on_status=False)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # --- transport ---
    def queue(self, workflow: dict) -> str:
        r = self.session.post(f"{self.base}/prompt",
                              json={"prompt": workflow, "client_id": self.client_id}, timeout=60)
        if r.status_code >= 400:                       # surface ComfyUI's node_errors, not a bare 400
            try:
                detail = json.dumps(r.json())[:1000]
            except Exception:
                detail = r.text[:1000]
            raise RuntimeError(f"/prompt rejected ({r.status_code}): {detail}")
        return r.json()["prompt_id"]

    def wait(self, prompt_id: str, poll: float = 2.0, timeout: float = 3600) -> dict:
        """Poll history until the job finishes. Tolerates the RunPod proxy briefly
        404-ing / ComfyUI restarting after an OOM: keeps polling while it's down, but
        if ComfyUI comes back up and the job has vanished (lost in a restart), fails
        fast so the caller can re-queue it."""
        deadline = time.time() + timeout
        down_since: float | None = None
        back_up_since: float | None = None
        saw_down = False
        while time.time() < deadline:
            try:
                r = self.session.get(f"{self.base}/history/{prompt_id}", timeout=30)
                status = r.status_code
            except requests.RequestException:
                status = 0
            if status == 0 or status == 404 or status >= 500:   # down / restarting / transient
                down_since = down_since or time.time()
                saw_down = True
                if time.time() - down_since > 240:
                    raise RuntimeError(f"ComfyUI unreachable >240s while awaiting {prompt_id}")
                time.sleep(poll)
                continue
            down_since = None
            hist = r.json()
            if prompt_id in hist:
                return hist[prompt_id]
            if saw_down:                                         # came back but job not here yet
                back_up_since = back_up_since or time.time()
                if time.time() - back_up_since > 30:             # ...it was lost in the restart
                    raise RuntimeError(f"prompt {prompt_id} lost after a ComfyUI restart")
            time.sleep(poll)
        raise TimeoutError(f"prompt {prompt_id} did not finish in {timeout}s")

    def outputs(self, history: dict) -> list[dict]:
        # grab any produced file dict, whatever key the node uses (images/gifs/videos/...)
        files = []
        for node in history.get("outputs", {}).values():
            for val in node.values():
                if isinstance(val, list):
                    files.extend(f for f in val if isinstance(f, dict) and f.get("filename"))
        return files

    def download(self, f: dict, dest: Path) -> Path:
        r = self.session.get(f"{self.base}/view",
                         params={"filename": f["filename"], "subfolder": f.get("subfolder", ""),
                                 "type": f.get("type", "output")}, timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest

    def upload(self, path: Path, kind: str = "input") -> dict:
        with open(path, "rb") as fh:
            r = self.session.post(f"{self.base}/upload/image",
                              files={"image": (path.name, fh)}, data={"type": kind}, timeout=120)
        r.raise_for_status()
        return r.json()

    # --- template helpers ---
    @staticmethod
    def load_template(name: str) -> dict:
        return json.loads((WORKFLOWS_DIR / PARAM_MAP[name]["file"]).read_text())

    @staticmethod
    def set(workflow: dict, node_id: str, field: str, value) -> None:
        workflow[node_id]["inputs"][field] = value

    def _apply(self, name: str, workflow: dict, **values) -> None:
        m = PARAM_MAP[name]
        for key, val in values.items():
            if key in m and m[key]:
                node_id, field = m[key]
                self.set(workflow, node_id, field, val)

    # --- high-level jobs (used by generate.py) ---
    def _run(self, name: str, dest: Path, **values) -> Path:
        if not PARAM_MAP[name]:
            raise RuntimeError(f"PARAM_MAP['{name}'] is empty — export {name}.json (Save API Format) "
                               f"and fill node ids first.")
        wf = self.load_template(name)
        self._apply(name, wf, **values)
        hist = self.wait(self.queue(wf))
        outs = self.outputs(hist)
        if not outs:
            raise RuntimeError(f"{name} produced no output{self._why(hist)}")
        return self.download(outs[-1], dest)

    @staticmethod
    def _why(hist: dict) -> str:
        """Pull the execution error out of a finished-but-empty history."""
        st = hist.get("status", {}) or {}
        bits = []
        for msg in st.get("messages", []):
            if isinstance(msg, list) and len(msg) == 2 and "error" in str(msg[0]).lower():
                data = msg[1] if isinstance(msg[1], dict) else {}
                bits.append(f"{data.get('exception_type', 'error')} in "
                            f"{data.get('node_type')}#{data.get('node_id')}: "
                            f"{data.get('exception_message')}")
        return (" -- " + " | ".join(bits)) if bits else f" (status={st.get('status_str')})"

    def qwen_still(self, prompt: str, negative: str, seed: int, w: int, h: int, dest: Path) -> Path:
        return self._run("qwen_still", dest, prompt=prompt, negative=negative, seed=seed, width=w, height=h)

    def wan_i2v(self, image: Path, prompt: str, frames: int, w: int, h: int, dest: Path) -> Path:
        up = self.upload(image)
        return self._run("wan_i2v", dest, image=up["name"], prompt=prompt,
                         frames=frames, width=w, height=h)

    def flux_still(self, prompt: str, w: int, h: int, dest: Path,
                   seed: int = 0, lora: float = 0.8, guidance: float = 3.5) -> Path:
        return self._run("flux_still", dest, prompt=prompt, width=w, height=h,
                         seed=seed, lora=lora, guidance=guidance)

    def wan22(self, image: Path, prompt: str, w: int, h: int, length: int,
              fps: int, dest: Path, seed: int = 0) -> Path:
        up = self.upload(image)
        return self._run("wan22", dest, image=up["name"], prompt=prompt,
                         width=w, height=h, length=length, fps=fps, seed=seed)

    def infinitetalk(self, avatar: Path, audio: Path, prompt: str, negative: str,
                     w: int, h: int, frames: int, dest: Path) -> Path:
        a_img = self.upload(avatar)
        a_wav = self.upload(audio, kind="input")
        return self._run("infinitetalk", dest, image=a_img["name"], audio=a_wav["name"],
                         prompt=prompt, negative=negative, width=w, height=h, frames=frames)

    def tts(self, text: str, ref_audio: Path, ref_text: str, dest: Path,
            seed: int = 1, speed: float = 1.0, nfe: int = 64, cfg: float = 2.0,
            cross_fade: float = 0.15, sway: float = -1.0) -> Path:
        """Clone the reference voice (F5-TTS) and speak `text`. Returns the audio path."""
        up = self.upload(Path(ref_audio), kind="input")
        return self._run("tts", dest, ref_audio=up["name"],
                         ref_text=ref_text, text=text, seed=seed, speed=speed,
                         nfe=nfe, cfg=cfg, cross_fade=cross_fade, sway=sway)
