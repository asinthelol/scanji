"""
manga-assist: tool for drafting and proofreading manga translations (JA -> EN).

Run:  uvicorn backend.main:app --reload
Config (via .env):
  ANTHROPIC_API_KEY   needed for AI drafting/proofreading
  MANGA_ASSIST_MODEL  optional model override
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import STATIC
from .routers import draft, export, ocr, pages, project

app = FastAPI(title="manga-assist")

for module in (project, pages, ocr, draft, export):
    app.include_router(module.router)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
