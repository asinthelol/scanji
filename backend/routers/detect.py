from pathlib import Path

from fastapi import APIRouter, HTTPException
from PIL import Image

from ..config import PAGES
from ..schemas import DetectReq, OrderReq
from ..services.detect import detect_text
from ..services.reading_order import reading_order

router = APIRouter(prefix="/api", tags=["detect"])


@router.post("/detect")
def detect(req: DetectReq):
    path = PAGES / Path(req.page).name
    if not path.exists():
        raise HTTPException(404, "page not found")
    img = Image.open(path).convert("RGB")
    return {"boxes": detect_text(img, req.threshold, req.include_free)}


@router.post("/reading-order")
def order(req: OrderReq):
    idx = reading_order([(b.x, b.y, b.w, b.h) for b in req.boxes])
    return {"ids": [req.boxes[i].id for i in idx]}
