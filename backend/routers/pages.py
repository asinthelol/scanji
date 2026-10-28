import io
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from ..config import PAGES
from ..storage import load_project, save_project

router = APIRouter(prefix="/api/pages", tags=["pages"])


@router.post("")
async def upload_page(file: UploadFile = File(...)):
    name = Path(file.filename or "page.png").name
    raw = await file.read()

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except Exception:
        raise HTTPException(400, "Not a valid image")

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
