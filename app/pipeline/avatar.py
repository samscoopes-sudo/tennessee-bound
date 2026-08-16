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

File paths are the one sharp edge: the Docker services read/write inside a
mounted data directory, so audio and face-video files must live under
`DUIX_DATA_DIR` and are passed to the API as names *relative to that mount*.
"""
from __future__ import annotations

import shutil
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
        timeout: float = 600.0,
    ) -> None:
        self.gen_video_url = (gen_video_url or config.DUIX_GEN_VIDEO_URL).rstrip("/")
        self.tts_url = (tts_url or config.DUIX_TTS_URL).rstrip("/")
        self.data_dir = Path(data_dir or config.DUIX_DATA_DIR)
        self.poll_interval = poll_interval
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.gen_video_url and self.data_dir)

    # -- staging -----------------------------------------------------------
    def _stage(self, src: Path, subdir: str) -> str:
        """Copy a local file into the mounted data dir, return its relative name.

        The Duix Docker services only see files under the mounted data volume,
        so anything we hand to the API has to be copied in first. We return the
        path *relative* to ``data_dir`` because that is what the API expects.
        """
        src = Path(src)
        if not src.exists():
            raise DuixAvatarError(f"input file does not exist: {src}")
        dest_dir = self.data_dir / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{uuid.uuid4().hex[:12]}{src.suffix}"
        shutil.copyfile(src, dest)
        return str(dest.relative_to(self.data_dir))

    # -- TTS (voice clone) -------------------------------------------------
    def tts(
        self,
        text: str,
        reference_audio: Path,
        reference_text: str = "",
        out_name: Optional[str] = None,
    ) -> str:
        """Synthesize ``text`` in the voice of ``reference_audio``.

        Returns the produced wav's path relative to ``data_dir`` (ready to
        pass straight to :meth:`synthesize`). ``reference_audio`` is a short
        clean sample of the target voice; ``reference_text`` is its transcript
        (improves cloning; may be left blank).
        """
        ref_rel = self._stage(reference_audio, "voice/data")
        out_name = out_name or f"tts/{uuid.uuid4().hex[:12]}.wav"
        (self.data_dir / out_name).parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "speaker": uuid.uuid4().hex[:12],
            "text": text,
            "format": "wav",
            "reference_audio": ref_rel,
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

        # The service writes the wav into the shared volume; persist the bytes
        # locally too so the path is populated even on a bind mount we can see.
        out_path = self.data_dir / out_name
        if r.headers.get("content-type", "").startswith("audio"):
            out_path.write_bytes(r.content)
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

        ``audio_path`` may be a local file or a name already relative to
        ``data_dir``; ditto ``face_video_path``. Blocks until the job finishes
        (or ``timeout`` elapses) and returns the local path of the result.
        """
        audio_rel = self._as_relative(audio_path, "voice/data")
        video_rel = self._as_relative(face_video_path, "face2face")
        code = uuid.uuid4().hex

        submit = {
            "audio_url": audio_rel,
            "video_url": video_rel,
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

    def _as_relative(self, path: Path, subdir: str) -> str:
        """Accept either an already-relative name or a local file to stage."""
        p = Path(path)
        if not p.is_absolute() and (self.data_dir / p).exists():
            return str(p)
        return self._stage(p, subdir)

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
        """Turn the API's result reference into a local path under data_dir."""
        candidate = self.data_dir / result
        if candidate.exists():
            return candidate
        # Some builds return a path already relative to face2face output.
        candidate = self.data_dir / "face2face" / result
        if candidate.exists():
            return candidate
        raise DuixAvatarError(
            f"result not found on shared volume: {result} (looked under {self.data_dir})"
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
            audio_rel = self.tts(script, voice_reference, voice_reference_text)
            audio = self.data_dir / audio_rel
        return self.synthesize(
            audio_path=audio,
            face_video_path=face_video,
            super_resolution=super_resolution,
        )
