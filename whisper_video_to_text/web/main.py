import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from whisper_video_to_text.convert import supported_media_accept_attribute
from whisper_video_to_text.web.views import router as web_router

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Whisper Video to Text Web")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _asset_version() -> int:
    """Return a static asset version for cache-busting browser CSS/JS."""
    asset_paths = [
        STATIC_DIR / "nord-theme.css",
        STATIC_DIR / "style.css",
        STATIC_DIR / "app.js",
    ]
    return int(max(path.stat().st_mtime for path in asset_paths if path.exists()))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main web interface."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "asset_version": _asset_version(),
            "media_accept": supported_media_accept_attribute(),
        },
    )


app.include_router(web_router)

if __name__ == "__main__":

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    uvicorn.run("whisper_video_to_text.web.main:app", host=host, port=port, reload=reload)
