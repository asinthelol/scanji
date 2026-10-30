from fastapi import APIRouter, HTTPException

from ..schemas import TitleReq
from ..storage import create_chapter, delete_chapter

router = APIRouter(prefix="/api/projects/{pid}/chapters", tags=["chapters"])


@router.post("", status_code=201)
def create(pid: str, req: TitleReq):
    title = req.title.strip()
    if not title:
        raise HTTPException(400, "Chapter name is required")
    return {"id": create_chapter(pid, title), "title": title}


@router.delete("/{cid}")
def delete(pid: str, cid: str):
    delete_chapter(pid, cid)
    return {"ok": True}
