import os

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from whisper_video_to_text.web.views import router as web_router

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Whisper Video to Text Web")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(web_router)

if __name__ == "__main__":

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    uvicorn.run("whisper_video_to_text.web.main:app", host=host, port=port, reload=reload)
