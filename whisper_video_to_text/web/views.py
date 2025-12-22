import json
import logging
import os
import shutil
import tempfile
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from whisper_video_to_text.convert import convert_mp4_to_mp3
from whisper_video_to_text.download import download_video
from whisper_video_to_text.transcribe import (
    save_srt,
    save_vtt,
    transcribe_audio,
)
from whisper_video_to_text.web.progress import (
    create_job,
    get_job,
    progress_stream,
    set_result_sync,
    update_progress_sync,
)

# Ensure uploads directory exists at module initialization
os.makedirs("uploads", exist_ok=True)

router = APIRouter()


@router.get("/events/{job_id}")
async def events(job_id: str) -> StreamingResponse | JSONResponse:
    """Stream SSE progress events for a job."""
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    async def event_generator():
        async for update in progress_stream(job_id):
            yield f"data: {json.dumps(update)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    
    tempdir = tempfile.mkdtemp(prefix="wvttmp_")
    try:
        mp4_path: str | None = None
        
        # Download or save uploaded file
        if url:
            update_progress_sync(job_id, 10, "downloading", "Downloading video...")
            mp4_path = download_video(url, output_dir=tempdir)
        elif file:
            update_progress_sync(job_id, 10, "uploading", "Saving uploaded file...")
            # Save uploaded file to uploads directory
            dest = os.path.join("uploads", file.filename or "upload.mp4")
            with open(dest, "wb") as f_out:
                shutil.copyfileobj(file.file, f_out)
            mp4_path = dest
        else:
            update_progress_sync(job_id, 100, "error", "No file or URL provided")
            return

        update_progress_sync(job_id, 30, "converting", "Extracting audio...")
        mp3_path = convert_mp4_to_mp3(mp4_path, verbose=False)

        update_progress_sync(job_id, 60, "transcribing", "Transcribing audio...")
        result = transcribe_audio(
            str(mp3_path), model_name=model, language=language, verbose=False
        )

        update_progress_sync(job_id, 90, "saving", "Preparing output...")
        
        # Build response with requested formats
        output: dict[str, Any] = {
            "text": result.get("text", ""),
            "language": result.get("language"),
            "formats": {},
        }
        
        # Generate outputs based on requested formats
        if "txt" in formats:
            if timestamps and result.get("segments"):
                # Include timestamps in text output
                lines = []
                for seg in result["segments"]:
                    start = seg.get("start", 0)
                    text = seg.get("text", "").strip()
                    lines.append(f"[{start:.2f}s] {text}")
                output["formats"]["txt"] = "\n".join(lines)
            else:
                output["formats"]["txt"] = result.get("text", "")
        
        if "srt" in formats:
            # Generate SRT content
            srt_lines = []
            for i, seg in enumerate(result.get("segments", []), 1):
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                text = seg.get("text", "").strip()
                srt_lines.append(str(i))
                srt_lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
                srt_lines.append(text)
                srt_lines.append("")
            output["formats"]["srt"] = "\n".join(srt_lines)
        
        if "vtt" in formats:
            # Generate VTT content
            vtt_lines = ["WEBVTT", ""]
            for seg in result.get("segments", []):
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                text = seg.get("text", "").strip()
                vtt_lines.append(f"{_format_vtt_time(start)} --> {_format_vtt_time(end)}")
                vtt_lines.append(text)
                vtt_lines.append("")
            output["formats"]["vtt"] = "\n".join(vtt_lines)

        update_progress_sync(job_id, 100, "complete", "Done")
        set_result_sync(job_id, output)
        
    except Exception as e:
        logging.exception(f"Transcription error for job {job_id}: {e}")
        update_progress_sync(job_id, 100, "error", f"Error: {e}")
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _format_vtt_time(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02}.{ms:03}"


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
    file = form.get("file")
    url = form.get("url")
    model = form.get("model", "base")
    language = form.get("language")
    formats_list = form.getlist("formats")
    formats = formats_list if formats_list else ["txt"]
    timestamps = str(form.get("timestamps", "false")).lower() == "true"

    # Start background task with user input
    background_tasks.add_task(
        run_transcription_task,
        job_id,
        file=file,
        url=url,
        model=model if isinstance(model, str) else "base",
        language=language if isinstance(language, str) else None,
        formats=formats,
        timestamps=timestamps,
    )
    return JSONResponse({"job_id": job_id})

