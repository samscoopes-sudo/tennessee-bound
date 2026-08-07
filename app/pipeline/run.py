"""Orchestrates the four steps into one job run."""
from __future__ import annotations

from pathlib import Path

from .. import config
from . import assets, compose, director, transcribe
from .models import Job, JobStatus


def run_job(job: Job, on_update=lambda j: None, energy: str = "balanced") -> Job:
    try:
        job.status = JobStatus.TRANSCRIBING
        on_update(job)
        transcript = transcribe.transcribe(job.source_path)

        job.status = JobStatus.DIRECTING
        on_update(job)
        edl = director.direct(transcript, energy=energy)
        edl.energy = energy
        job.edl = edl

        job.status = JobStatus.SOURCING_ASSETS
        on_update(job)
        assets.source_assets(edl)

        job.status = JobStatus.COMPOSING
        on_update(job)
        out = str(config.WORK_DIR / f"{job.id}_edited.mp4")
        compose.compose(edl, job.source_path, out)

        job.output_path = out
        job.status = JobStatus.DONE
        job.message = "Done"
    except Exception as e:  # surface the failure to the UI
        job.status = JobStatus.FAILED
        job.message = f"{type(e).__name__}: {e}"
    on_update(job)
    return job
