from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..schemas import ExportSettings
from ..storage import load_project

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("", response_class=PlainTextResponse)
def export_script():
    proj = load_project()
    settings = ExportSettings(**proj.get("export", {}))
    title = proj.get("title") or "Translation script"

    lines = []
    if settings.title_heading:
        lines += [settings.title_heading.replace("{title}", title), ""]
    for page, boxes in proj["pages"].items():  # already in natural order
        
         # Removed line indexing bc extensions like TyperTools in Photoshop doesn't ignore them.
        texts = [b.get("final") or b.get("draft") or b.get("suggestion") or "" for b in boxes]
        texts = [t.strip() for t in texts if t.strip()]
        if not texts:
            continue
        if settings.page_heading:
            lines.append(settings.page_heading.replace("{page}", page))
        lines.extend(texts)
        lines.append("")
    return "\n".join(lines)
