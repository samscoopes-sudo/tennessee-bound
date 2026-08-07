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
