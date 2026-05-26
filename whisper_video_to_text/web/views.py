from __future__ import annotations

import json
import logging
import os
import shutil
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.datastructures import UploadFile

from whisper_video_to_text.convert import (
    SUPPORTED_MEDIA_EXTENSIONS,
    supported_media_extensions_display,
)
from whisper_video_to_text.errors import TranscriptionCancelled
from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription
from whisper_video_to_text.web.progress import (
    create_job,
    get_job,
    is_cancel_requested,
    progress_stream,
    request_cancel_sync,
    set_cancelled_sync,
    set_result_sync,
    update_progress_sync,
)

# Ensure uploads directory exists at module initialization
os.makedirs("uploads", exist_ok=True)
os.makedirs("transcripts", exist_ok=True)

router = APIRouter()


@router.get("/events/{job_id}")
async def events(job_id: str) -> StreamingResponse:
    """Stream SSE progress events for a job."""
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)  # type: ignore[return-value]

    async def event_generator() -> AsyncGenerator[str, None]:
        async for update in progress_stream(job_id):
            yield f"data: {json.dumps(update)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/download/{job_id}/{extension}")
async def download_file(job_id: str, extension: str) -> FileResponse:
    """Download a transcript file by job ID and extension."""
    if extension not in ["txt", "srt", "vtt"]:
        raise HTTPException(status_code=400, detail="Invalid extension")

    file_path = os.path.join("transcripts", f"{job_id}.{extension}")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path, media_type="text/plain", filename=f"transcript-{job_id}.{extension}"
    )


@router.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> JSONResponse:
    """Request cancellation of an in-progress job."""
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    if job.status in {"complete", "error", "cancelled"}:
        return JSONResponse({"job_id": job_id, "status": job.status})

    request_cancel_sync(job_id)
    return JSONResponse({"job_id": job_id, "status": "cancel_requested"})


@router.get("/api/history")
async def get_history() -> list[dict[str, Any]]:
    """List all available transcripts."""
    transcripts_dir = Path("transcripts")
    if not transcripts_dir.exists():
        return []

    # Group files by job_id
    jobs: dict[str, dict[str, Any]] = {}

    for file_path in transcripts_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith("."):
            # Expecting filename format: {job_id}.{extension}
            parts = file_path.name.split(".")
            if len(parts) < 2:
                continue

            extension = parts[-1]
            job_id = ".".join(parts[:-1])

            if extension not in ["txt", "srt", "vtt"]:
                continue

            if job_id not in jobs:
                # Use modification time of the first file found for this job
                mtime = file_path.stat().st_mtime
                jobs[job_id] = {
                    "job_id": job_id,
                    "date": datetime.fromtimestamp(mtime).isoformat(),
                    "formats": [],
                }

            jobs[job_id]["formats"].append(extension)

    # Convert to list and sort by date descending
    history = list(jobs.values())
    history.sort(key=lambda x: x["date"], reverse=True)

    return history


def run_transcription_task(
    job_id: str,
    file: UploadFile | None = None,
    url: str | None = None,
    model: str = "base",
    language: str | None = None,
    formats: list[str] | None = None,
    timestamps: bool = False,
) -> None:
    """Run transcription task synchronously in a background thread.

    This function is called by FastAPI's BackgroundTasks in a thread pool.
    It uses synchronous progress updates to communicate with the async SSE stream.

    Args:
        job_id: Unique job identifier
        file: Uploaded file object
        url: URL to download video from
        model: Whisper model name
        language: Language code for transcription
        formats: List of output formats (txt, srt, vtt)
        timestamps: Whether to include timestamps in txt output
    """
    if formats is None:
        formats = ["txt"]

    try:
        # Resolve source: save upload to disk, or pass URL directly to pipeline
        if url:
            source = url
            download = True
            update_progress_sync(job_id, 5, "starting", "Starting download...")
        elif file:
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in SUPPORTED_MEDIA_EXTENSIONS:
                msg = (
                    f"Unsupported file type '{suffix}'. "
                    f"Supported: {supported_media_extensions_display()}"
                )
                update_progress_sync(job_id, 100, "error", msg)
                return
            update_progress_sync(job_id, 5, "uploading", "Saving uploaded file...")
            dest = os.path.join("uploads", f"{job_id}{suffix}")
            with open(dest, "wb") as f_out:
                shutil.copyfileobj(file.file, f_out)
            source = dest
            download = False
        else:
            update_progress_sync(job_id, 100, "error", "No file or URL provided")
            return

        request = TranscriptionRequest(
            source=source,
            download=download,
            model=model,
            language=language,
            formats=tuple(formats),
            include_timestamps=timestamps,
            output_base=Path("transcripts") / job_id,
        )
        result = run_transcription(
            request,
            progress=lambda pct, status, msg: update_progress_sync(job_id, pct, status, msg),
            should_cancel=lambda: is_cancel_requested(job_id),
        )

        # Whisper is blocking; cancellation requested during it surfaces here.
        if is_cancel_requested(job_id):
            set_cancelled_sync(job_id)
            return

        set_result_sync(
            job_id,
            {
                "text": result.text,
                "language": result.language,
                "formats": result.rendered,
            },
        )

    except TranscriptionCancelled:
        set_cancelled_sync(job_id)
    except Exception as e:
        logging.exception(f"Transcription error for job {job_id}: {e}")
        update_progress_sync(job_id, 100, "error", f"Error: {e}")


@router.post("/api/transcribe")
async def transcribe_api(
    background_tasks: BackgroundTasks,
    request: Request,
) -> JSONResponse:
    """Start a transcription job and return the job ID."""
    # Create a new job
    job_id = create_job()

    # Get form data from request
    form = await request.form()
    _file = form.get("file")
    file: UploadFile | None = _file if isinstance(_file, UploadFile) else None
    _url = form.get("url")
    url: str | None = _url if isinstance(_url, str) else None
    _model = form.get("model", "base")
    model: str = _model if isinstance(_model, str) else "base"
    _language = form.get("language")
    language: str | None = _language if isinstance(_language, str) and _language else None
    formats: list[str] = [f for f in form.getlist("formats") if isinstance(f, str)] or ["txt"]
    timestamps = str(form.get("timestamps", "false")).lower() == "true"

    # Start background task with user input
    background_tasks.add_task(
        run_transcription_task,
        job_id,
        file=file,
        url=url,
        model=model,
        language=language,
        formats=formats,
        timestamps=timestamps,
    )
    return JSONResponse({"job_id": job_id})
