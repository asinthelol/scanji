from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..storage import load_project

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("", response_class=PlainTextResponse)
def export_script():
    proj = load_project()
    lines = [f"# {proj.get('title') or 'Translation script'}", ""]
    for page, boxes in proj["pages"].items():  # already in natural order
        
        # Removed line indexing bc TyperTools in Photoshop doesn't ignore them.
        texts = [b.get("final") or b.get("draft") or b.get("suggestion") or "" for b in boxes]
        texts = [t.strip() for t in texts if t.strip()]
        if not texts:
            continue
        lines.append(f"## {page}")
        lines.extend(texts)
        lines.append("")
    return "\n".join(lines)
