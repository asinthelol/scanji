"""data/projects/<id>/project.json plus pages/<chapter-id>/ image folders per project."""
import json
import re
import shutil
import unicodedata
from pathlib import Path

from fastapi import HTTPException

from .config import LEGACY_PAGES, LEGACY_PROJECT_FILE, PROJECTS

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def natural_key(name: str) -> list:
    """
    Sort key so that "2.jpg" comes before "10.jpg".
    """
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", name)]


def slugify(name: str, fallback: str = "project") -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or fallback


def unique_id(base: str, taken: set[str]) -> str:
    """base, or base-2, base-3, ... when it is already taken."""
    candidate, n = base, 1
    while candidate in taken:
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def empty_project(title: str = "") -> dict:
    return {"title": title, "context": "", "glossary": [], "chapters": []}


def project_dir(pid: str) -> Path:
    """
    Folder of an existing project; 404 for unknown or malformed ids (also blocks path tricks).
    """
    if not _ID_RE.match(pid) or not (PROJECTS / pid).is_dir():
        raise HTTPException(404, "project not found")
    return PROJECTS / pid


def chapter_dir(pid: str, cid: str) -> Path:
    """
    Image folder of an existing chapter; 404 for unknown or malformed ids.
    """
    folder = project_dir(pid) / "pages" / cid
    if not _ID_RE.match(cid) or not folder.is_dir():
        raise HTTPException(404, "chapter not found")
    return folder


def get_chapter(proj: dict, cid: str) -> dict:
    for chapter in proj["chapters"]:
        if chapter["id"] == cid:
            return chapter
    raise HTTPException(404, "chapter not found")


def _normalized(p: dict) -> dict:
    """
    Chapters and their pages in natural order, so project.json reads in reading order.
    """
    for chapter in p.get("chapters", []):
        chapter["pages"] = {k: chapter["pages"][k] for k in sorted(chapter.get("pages", {}), key=natural_key)}
    p["chapters"] = sorted(p.get("chapters", []), key=lambda c: natural_key(c.get("title") or c["id"]))
    return p


def _write(pid: str, p: dict) -> None:
    (project_dir(pid) / "project.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project(pid: str) -> dict:
    file = project_dir(pid) / "project.json"
    return _normalized(json.loads(file.read_text(encoding="utf-8")) if file.exists() else empty_project())


def save_project(pid: str, p: dict) -> None:
    _write(pid, _normalized(p))


def list_projects() -> list[dict]:
    """
    Summaries, most recently modified first.
    """
    rows = []
    for d in PROJECTS.iterdir():
        file = d / "project.json"
        if not d.is_dir() or not file.exists():
            continue
        proj = json.loads(file.read_text(encoding="utf-8"))
        chapters = proj.get("chapters", [])
        rows.append(
            {
                "id": d.name,
                "title": proj.get("title") or d.name,
                "chapters": len(chapters),
                "pages": sum(len(c["pages"]) for c in chapters),
                "bubbles": sum(len(b) for c in chapters for b in c["pages"].values()),
                "updated": file.stat().st_mtime,
            }
        )
    return sorted(rows, key=lambda r: -r["updated"])


def create_project(title: str) -> str:
    pid = unique_id(slugify(title), {d.name for d in PROJECTS.iterdir()})
    (PROJECTS / pid / "pages").mkdir(parents=True)
    save_project(pid, empty_project(title))
    return pid


def delete_project(pid: str) -> None:
    shutil.rmtree(project_dir(pid))


def create_chapter(pid: str, title: str) -> str:
    proj = load_project(pid)
    cid = unique_id(slugify(title, "chapter"), {c["id"] for c in proj["chapters"]})
    (project_dir(pid) / "pages" / cid).mkdir(parents=True)
    proj["chapters"].append({"id": cid, "title": title, "pages": {}})
    save_project(pid, proj)
    return cid


def delete_chapter(pid: str, cid: str) -> None:
    proj = load_project(pid)
    get_chapter(proj, cid)
    shutil.rmtree(chapter_dir(pid, cid))
    proj["chapters"] = [c for c in proj["chapters"] if c["id"] != cid]
    save_project(pid, proj)


def migrate_legacy() -> None:
    """
    Move the old single-project layout (data/project.json + data/pages/) into a project folder.
    """
    if not LEGACY_PROJECT_FILE.exists():
        return
    proj = json.loads(LEGACY_PROJECT_FILE.read_text(encoding="utf-8"))
    pid = create_project(proj.get("title") or "Imported project")
    if LEGACY_PAGES.is_dir():
        shutil.rmtree(PROJECTS / pid / "pages")
        shutil.move(str(LEGACY_PAGES), PROJECTS / pid / "pages")
    proj.pop("chapters", None)
    _write(pid, proj)  # still flat: migrate_chapters() below turns it into a chapter
    LEGACY_PROJECT_FILE.unlink()


def migrate_chapters() -> None:
    """
    Projects used to hold their pages directly. Wrap those pages in a "Chapter 1" and move
    the images into its folder. Images that were uploaded but never registered are picked up too.
    """
    for d in PROJECTS.iterdir():
        file = d / "project.json"
        if not file.exists():
            continue
        proj = json.loads(file.read_text(encoding="utf-8"))
        if "chapters" in proj:
            continue
        pages = proj.pop("pages", {})
        target = d / "pages" / "chapter-1"
        target.mkdir(parents=True, exist_ok=True)
        for f in list((d / "pages").iterdir()):
            if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES:
                pages.setdefault(f.name, [])
                shutil.move(str(f), target / f.name)
        proj["chapters"] = [{"id": "chapter-1", "title": "Chapter 1", "pages": pages}]
        _write(d.name, _normalized(proj))
