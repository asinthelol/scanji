from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..schemas import ExportSettings
from ..storage import get_chapter, load_project

router = APIRouter(prefix="/api/projects/{pid}/chapters/{cid}/export", tags=["export"])


@router.get("", response_class=PlainTextResponse)
def export_script(pid: str, cid: str):
    proj = load_project(pid)
    chapter = get_chapter(proj, cid)
    settings = ExportSettings(**proj.get("export", {}))
    title = proj.get("title") or "Translation script"

    lines = []
    if settings.title_heading:
        lines += [settings.title_heading.replace("{title}", title).replace("{chapter}", chapter["title"]), ""]
    for page, boxes in chapter["pages"].items():  # already in natural order
        # No line numbering: translators' tools (e.g. TyperTools in Photoshop) do not skip it.
        texts = [b.get("final") or b.get("draft") or b.get("suggestion") or "" for b in boxes]
        texts = [t.strip() for t in texts if t.strip()]
        if not texts:
            continue
        if settings.page_heading:
            lines.append(settings.page_heading.replace("{page}", page))
        lines.extend(texts)
        lines.append("")
    return "\n".join(lines)
