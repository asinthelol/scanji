from fastapi import APIRouter

from ..schemas import DraftReq
from ..services import llm

router = APIRouter(prefix="/api/draft", tags=["draft"])


@router.post("")
def draft(req: DraftReq):
    return llm.draft(req)
