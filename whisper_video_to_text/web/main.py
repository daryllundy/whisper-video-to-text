from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Whisper Video to Text Web")
templates = Jinja2Templates(directory="whisper_video_to_text/web/templates")
app.mount("/static", StaticFiles(directory="whisper_video_to_text/web/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from whisper_video_to_text.web.views import router as web_router
app.include_router(web_router)

if __name__ == "__main__":
    import os
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "whisper_video_to_text.web.main:app",
        host=host,
        port=port,
        reload=reload
    )
