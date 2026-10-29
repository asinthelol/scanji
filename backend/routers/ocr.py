from pathlib import Path

from fastapi import APIRouter, HTTPException
from PIL import Image

from ..schemas import OcrReq
from ..services.ocr import get_ocr
from ..storage import pages_dir

router = APIRouter(prefix="/api/projects/{pid}/ocr", tags=["ocr"])


@router.post("")
def ocr_region(pid: str, req: OcrReq):
    path = pages_dir(pid) / Path(req.page).name
    if not path.exists():
        raise HTTPException(404, "page not found")

    img = Image.open(path).convert("RGB")
    box = (int(req.x), int(req.y), int(req.x + req.w), int(req.y + req.h))
    crop = img.crop(box)
    if crop.width < 4 or crop.height < 4:
        raise HTTPException(400, "region too small")

    text = get_ocr()(crop)
    return {"ja": text}
