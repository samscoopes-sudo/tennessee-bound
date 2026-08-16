"""Duix.Avatar (a.k.a. Heygem) adapter - generate the talking-head source.

The rest of this app *edits* a talking-head video: it lays b-roll, motion
graphics and text over an avatar you supply. This module fills the step
*before* that - it produces the avatar clip itself from a script, so a user
never has to record themselves on camera.

It talks to a locally deployed Duix.Avatar backend
(https://github.com/duixcom/Duix-Avatar), which runs three Docker services:

    guiji2025/fish-speech-ziming   TTS / voice clone   :18180
    guiji2025/fun-asr              ASR                 :10095
    guiji2025/duix.avatar          face2face synthesis :8383

Only TTS (:18180) and the face2face synthesizer (:8383) are needed here.

Everything is offline and GPU-bound, so this file only submits work and polls
for the result - it does no synthesis itself. Missing config just disables the
feature (mirrors how the asset ladder degrades), so importing the app never
requires a Duix backend to be running.

File paths are the sharp edge. The Duix compose mounts two host folders under
``DUIX_DATA_DIR`` straight onto each service's ``/code/data``:

    <DUIX_DATA_DIR>/voice/data  -> TTS service       (:18180)
    <DUIX_DATA_DIR>/face2face   -> face2face service (:8383)

Because each service sees its own folder *as* ``/code/data``, the API wants
**bare filenames**, not sub-paths. So we stage the driving audio and the face
video into ``face2face/`` and hand the synthesizer just their filenames; the
voice-clone reference goes into ``voice/data/`` for the TTS service.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

from .. import config


class DuixAvatarError(RuntimeError):
    """Raised when the Duix backend is unreachable or a job fails."""


class DuixAvatarClient:
    """Thin client over the Duix.Avatar TTS + face2face HTTP APIs.

    Parameters default to the values in ``config`` so callers can just do
    ``DuixAvatarClient().generate_talking_head(...)``.
    """

    def __init__(
        self,
        gen_video_url: Optional[str] = None,
        tts_url: Optional[str] = None,
        data_dir: Optional[Path] = None,
        poll_interval: float = 3.0,
        timeout: float = 1800.0,
    ) -> None:
        self.gen_video_url = (gen_video_url or config.DUIX_GEN_VIDEO_URL).rstrip("/")
        self.tts_url = (tts_url or config.DUIX_TTS_URL).rstrip("/")
        self.data_dir = Path(data_dir or config.DUIX_DATA_DIR)
        # The two host folders the Duix services mount as their /code/data.
        self.face_dir = self.data_dir / "face2face"
        self.voice_dir = self.data_dir / "voice" / "data"
        self.poll_interval = poll_interval
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.gen_video_url and self.data_dir)

    # -- staging -----------------------------------------------------------
    def _stage(self, src: Path, dest_dir: Path) -> str:
        """Copy a local file into ``dest_dir``; return its **bare filename**.

        The Duix services only see files inside their mounted folder, which
        they treat as ``/code/data``. The API therefore expects a filename with
        no directory part - so that is what we return.
        """
        src = Path(src)
        if not src.exists():
            raise DuixAvatarError(f"input file does not exist: {src}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex[:12]}{src.suffix}"
        (dest_dir / name).write_bytes(src.read_bytes())
        return name

    def _ensure_in_face(self, path: Path) -> str:
        """Return a bare filename that exists in ``face_dir``, staging if needed.

        Accepts a bare name already present in face2face, or any local file
        (which is copied in).
        """
        p = Path(path)
        if p.parent == Path(".") and (self.face_dir / p).exists():
            return p.name
        if p.parent == self.face_dir and p.exists():
            return p.name
        return self._stage(p, self.face_dir)

    # -- TTS (voice clone) -------------------------------------------------
    def tts(
        self,
        text: str,
        reference_audio: Path,
        reference_text: str = "",
    ) -> str:
        """Synthesize ``text`` in the voice of ``reference_audio``.

        Returns the produced wav's **bare filename inside face2face/**, ready to
        pass straight to :meth:`synthesize`. ``reference_audio`` is a short clean
        sample of the target voice; ``reference_text`` is its transcript
        (improves cloning; may be left blank).
        """
        ref_name = self._stage(reference_audio, self.voice_dir)

        payload = {
            "speaker": uuid.uuid4().hex[:12],
            "text": text,
            "format": "wav",
            "reference_audio": ref_name,
            "reference_text": reference_text,
        }
        try:
            r = httpx.post(
                f"{self.tts_url}/v1/preprocess_and_tts",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise DuixAvatarError(f"TTS request failed: {e}") from e

        # Write the narration into face2face/ so the synthesizer can read it.
        self.face_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{uuid.uuid4().hex[:12]}.wav"
        (self.face_dir / out_name).write_bytes(r.content)
        return out_name

    # -- face2face synthesis ----------------------------------------------
    def synthesize(
        self,
        audio_path: Path,
        face_video_path: Path,
        super_resolution: bool = False,
        watermark: bool = False,
    ) -> Path:
        """Drive ``face_video_path`` with ``audio_path`` -> a talking-head mp4.

        Both inputs may be local files or bare names already in ``face2face/``.
        Blocks until the job finishes (or ``timeout`` elapses) and returns the
        local path of the result.
        """
        audio_name = self._ensure_in_face(audio_path)
        video_name = self._ensure_in_face(face_video_path)
        code = uuid.uuid4().hex

        submit = {
            "audio_url": audio_name,
            "video_url": video_name,
            "code": code,
            "chaofen": 1 if super_resolution else 0,
            "watermark_switch": 1 if watermark else 0,
            "pn": 1,
        }
        try:
            r = httpx.post(
                f"{self.gen_video_url}/easy/submit",
                json=submit,
                timeout=self.timeout,
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise DuixAvatarError(f"submit failed: {e}") from e

        return self._poll(code)

    def _poll(self, code: str) -> Path:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                r = httpx.get(
                    f"{self.gen_video_url}/easy/query",
                    params={"code": code},
                    timeout=30,
                )
                r.raise_for_status()
                body = r.json()
            except httpx.HTTPError as e:
                raise DuixAvatarError(f"query failed: {e}") from e

            data = body.get("data") or {}
            status = data.get("status")
            # Duix status codes: 1 queued, 2 running, 3 success, 4 failed.
            if status == 3:
                result = data.get("result") or data.get("url")
                if not result:
                    raise DuixAvatarError("job succeeded but returned no result path")
                return self._resolve_result(result)
            if status == 4:
                raise DuixAvatarError(f"synthesis failed: {data.get('msg') or body}")

            time.sleep(self.poll_interval)
        raise DuixAvatarError(f"synthesis timed out after {self.timeout:.0f}s")

    def _resolve_result(self, result: str) -> Path:
        """Turn the API's result reference into a local path we can read.

        The synthesizer writes into its /code/data, i.e. our ``face2face/``, so
        the result is normally a bare filename there. Fall back to a couple of
        other likely spots before giving up.
        """
        name = Path(result).name
        for candidate in (
            self.face_dir / name,
            self.face_dir / result,
            self.data_dir / result,
        ):
            if candidate.exists():
                return candidate
        raise DuixAvatarError(
            f"result not found on shared volume: {result} (looked under {self.face_dir})"
        )

    # -- high level --------------------------------------------------------
    def generate_talking_head(
        self,
        face_video: Path,
        script: str,
        voice_reference: Optional[Path] = None,
        voice_reference_text: str = "",
        audio: Optional[Path] = None,
        super_resolution: bool = False,
    ) -> Path:
        """One call: script (+ face) -> finished talking-head mp4.

        Provide the speech one of two ways:
          * ``audio`` - a ready-made narration file (most reliable), or
          * ``voice_reference`` - a voice sample; ``script`` is then spoken in
            that cloned voice via the TTS service.
        """
        if not self.enabled:
            raise DuixAvatarError(
                "Duix.Avatar is not configured (set DUIX_GEN_VIDEO_URL / DUIX_DATA_DIR)"
            )
        if audio is None:
            if voice_reference is None:
                raise DuixAvatarError("provide either `audio` or `voice_reference`")
            audio = self.tts(script, voice_reference, voice_reference_text)
        return self.synthesize(
            audio_path=audio,
            face_video_path=face_video,
            super_resolution=super_resolution,
        )
