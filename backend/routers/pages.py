import io
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from ..storage import chapter_dir, get_chapter, load_project, save_project

router = APIRouter(prefix="/api/projects/{pid}/chapters/{cid}/pages", tags=["pages"])


def unique_name(folder: Path, name: str) -> str:
    """
    Avoid overwriting an existing page: page.png -> page-1.png.
    """
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate, n = name, 0
    while (folder / candidate).exists():
        n += 1
        candidate = f"{stem}-{n}{suffix}"
    return candidate


@router.post("")
async def upload_page(pid: str, cid: str, file: UploadFile = File(...)):
    folder = chapter_dir(pid, cid)
    name = Path(file.filename or "page.png").name
    raw = await file.read()

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except Exception:
        raise HTTPException(400, "Not a valid image")

    proj = load_project(pid)
    chapter = get_chapter(proj, cid)
    name = unique_name(folder, name)
    (folder / name).write_bytes(raw)
    chapter["pages"].setdefault(name, [])
    save_project(pid, proj)

    return {"name": name}


@router.get("/{name}")
def get_page(pid: str, cid: str, name: str):
    path = chapter_dir(pid, cid) / Path(name).name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)
