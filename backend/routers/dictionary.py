from fastapi import APIRouter

from ..services.dictionary import lookup

router = APIRouter(prefix="/api/dictionary", tags=["dictionary"])


@router.get("")
def search(q: str = ""):
    return lookup(q)
