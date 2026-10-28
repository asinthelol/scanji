from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..storage import load_project

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("", response_class=PlainTextResponse)
def export_script():
    proj = load_project()
    lines = [f"# {proj.get('title') or 'Translation script'}", ""]
    for page in sorted(proj["pages"]):
        boxes = proj["pages"][page]
        if not boxes:
            continue
        lines.append(f"## {page}")
        for i, b in enumerate(boxes, 1):
            en = b.get("final") or b.get("draft") or b.get("suggestion") or ""
            lines.append(f"{i}. {en}")
        lines.append("")
    return "\n".join(lines)
