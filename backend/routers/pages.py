import io
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from ..config import PAGES
from ..storage import load_project, save_project

router = APIRouter(prefix="/api/pages", tags=["pages"])


def unique_name(name: str) -> str:
    """
    Avoid overwriting an existing page: page.png -> page-1.png.
    """
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate, n = name, 0
    while (PAGES / candidate).exists():
        n += 1
        candidate = f"{stem}-{n}{suffix}"
    return candidate


@router.post("")
async def upload_page(file: UploadFile = File(...)):
    name = Path(file.filename or "page.png").name
    raw = await file.read()

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except Exception:
        raise HTTPException(400, "Not a valid image")

    name = unique_name(name)
    (PAGES / name).write_bytes(raw)
    proj = load_project()
    proj["pages"].setdefault(name, [])
    save_project(proj)

    return {"name": name}


@router.get("/{name}")
def get_page(name: str):
    path = PAGES / Path(name).name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)
