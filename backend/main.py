"""
Scanji: tool for drafting and proofreading manga translations (JA -> EN).

Run:  uvicorn backend.main:app --reload
Config (via .env):
  ANTHROPIC_API_KEY   needed for AI drafting/proofreading
  SCANJI_MODEL  optional model override

In development run `npm run dev` in frontend (it proxies /api to this server);
for normal use run `npm run build` and this server serves frontend/dist.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST
from .routers import chapters, detect, draft, export, ocr, pages, projects
from .storage import migrate_chapters, migrate_legacy



@asynccontextmanager
async def lifespan(_: FastAPI):
    # at startup, not import, so importing the app never touches data/
    migrate_legacy()
    migrate_chapters()
    yield


app = FastAPI(title="Scanji", lifespan=lifespan)

for module in (projects, chapters, pages, ocr, detect, draft, export):
    app.include_router(module.router)


@app.get("/", include_in_schema=False)
def index():
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        return PlainTextResponse(
            "Frontend not built. Run `npm install && npm run build` in frontend/, "
            "or use `npm run dev` there.",
            status_code=503,
        )
    return FileResponse(index_file)


if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str):
    """
    Client-side routes (e.g. /p/<id>) must load the app on refresh.
    """
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404)
    return index()
