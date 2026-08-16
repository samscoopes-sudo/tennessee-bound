"""FastAPI app: upload a raw avatar video, get back an edited one.

In-memory job store + background thread per job. Fine for a single-instance
deploy (Render/Railway/Fly free tier). Swap for a real queue if you scale out.
"""
from __future__ import annotations

import threading
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import config
from .pipeline.avatar import DuixAvatarClient, DuixAvatarError
from .pipeline.models import Job, JobStatus
from .pipeline.run import run_job

app = FastAPI(title="Video Agent - b-roll & motion graphics")

_JOBS: dict[str, Job] = {}
_LOCK = threading.Lock()


def _save_job(job: Job) -> None:
    with _LOCK:
        _JOBS[job.id] = job


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text()


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "director_model": config.DIRECTOR_MODEL,
        "asset_sources_enabled": config.enabled_asset_sources(),
        "has_anthropic_key": bool(config.ANTHROPIC_API_KEY),
        "duix_avatar_enabled": config.duix_avatar_enabled(),
    }


@app.post("/api/jobs")
def create_job(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    energy: str = Form("balanced"),
) -> JSONResponse:
    if not config.ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY is not configured on the server")

    job_id = uuid.uuid4().hex[:12]
    src = config.WORK_DIR / f"{job_id}_source{Path(file.filename or '').suffix or '.mp4'}"
    with open(src, "wb") as f:
        f.write(file.file.read())

    job = Job(id=job_id, source_path=str(src), status=JobStatus.QUEUED)
    _save_job(job)

    background.add_task(run_job, job, _save_job, energy)
    return JSONResponse({"id": job_id, "status": job.status})


def _run_avatar_job(
    job: Job,
    face_video: str,
    script: str,
    audio: str | None,
    voice_ref: str | None,
    voice_ref_text: str,
    energy: str,
) -> None:
    """Generate the talking-head with Duix.Avatar, then run the edit pipeline."""
    try:
        job.status = JobStatus.GENERATING_AVATAR
        _save_job(job)
        client = DuixAvatarClient()
        result = client.generate_talking_head(
            face_video=Path(face_video),
            script=script,
            audio=Path(audio) if audio else None,
            voice_reference=Path(voice_ref) if voice_ref else None,
            voice_reference_text=voice_ref_text,
        )
        # Hand the generated clip to the normal editing pipeline as its source.
        src = config.WORK_DIR / f"{job.id}_source{Path(result).suffix or '.mp4'}"
        if Path(result) != src:
            src.write_bytes(Path(result).read_bytes())
        job.source_path = str(src)
    except DuixAvatarError as e:
        job.status = JobStatus.FAILED
        job.message = f"avatar generation failed: {e}"
        _save_job(job)
        return
    run_job(job, _save_job, energy)


@app.post("/api/avatar-jobs")
def create_avatar_job(
    background: BackgroundTasks,
    script: str = Form(...),
    face_video: UploadFile = File(...),
    audio: UploadFile | None = File(None),
    voice_reference: UploadFile | None = File(None),
    voice_reference_text: str = Form(""),
    energy: str = Form("balanced"),
) -> JSONResponse:
    """Generate a talking-head from a script, then edit it - no camera needed.

    Supply the speech via `audio` (a ready narration) or `voice_reference`
    (a voice sample cloned onto the script). `face_video` is the reference
    face to animate.
    """
    if not config.ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY is not configured on the server")
    if not config.duix_avatar_enabled():
        raise HTTPException(
            503, "Duix.Avatar is not configured (set DUIX_GEN_VIDEO_URL / DUIX_DATA_DIR)"
        )
    if audio is None and voice_reference is None:
        raise HTTPException(400, "provide either `audio` or `voice_reference`")

    job_id = uuid.uuid4().hex[:12]

    def _save_upload(upload: UploadFile | None, label: str) -> str | None:
        if upload is None:
            return None
        dest = config.WORK_DIR / f"{job_id}_{label}{Path(upload.filename or '').suffix}"
        with open(dest, "wb") as f:
            f.write(upload.file.read())
        return str(dest)

    face_path = _save_upload(face_video, "face")
    audio_path = _save_upload(audio, "narration")
    voice_path = _save_upload(voice_reference, "voiceref")

    job = Job(id=job_id, status=JobStatus.QUEUED)
    _save_job(job)
    background.add_task(
        _run_avatar_job,
        job,
        face_path,
        script,
        audio_path,
        voice_path,
        voice_reference_text,
        energy,
    )
    return JSONResponse({"id": job_id, "status": job.status})


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> JSONResponse:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return JSONResponse(
        {
            "id": job.id,
            "status": job.status,
            "message": job.message,
            "has_output": bool(job.output_path),
            "cue_count": len(job.edl.cues) if job.edl else 0,
        }
    )


@app.get("/api/jobs/{job_id}/edl")
def get_edl(job_id: str) -> JSONResponse:
    job = _JOBS.get(job_id)
    if not job or not job.edl:
        raise HTTPException(404, "no EDL yet")
    return JSONResponse(job.edl.model_dump())


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str) -> FileResponse:
    job = _JOBS.get(job_id)
    if not job or not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(404, "output not ready")
    return FileResponse(job.output_path, media_type="video/mp4", filename="edited.mp4")
