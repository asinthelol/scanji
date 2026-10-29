"""data/projects/<id>/project.json plus a pages/ folder per project."""
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


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "project"


def empty_project(title: str = "") -> dict:
    return {"title": title, "context": "", "glossary": [], "pages": {}}


def project_dir(pid: str) -> Path:
    """
    Folder of an existing project; 404 for unknown or malformed ids (also blocks path tricks).
    """
    if not _ID_RE.match(pid) or not (PROJECTS / pid).is_dir():
        raise HTTPException(404, "project not found")
    return PROJECTS / pid


def pages_dir(pid: str) -> Path:
    return project_dir(pid) / "pages"


def load_project(pid: str) -> dict:
    file = project_dir(pid) / "project.json"
    proj = json.loads(file.read_text(encoding="utf-8")) if file.exists() else empty_project()
    proj["pages"] = {k: proj["pages"][k] for k in sorted(proj.get("pages", {}), key=natural_key)}
    return proj


def save_project(pid: str, p: dict) -> None:
    p["pages"] = {k: p["pages"][k] for k in sorted(p.get("pages", {}), key=natural_key)}
    (project_dir(pid) / "project.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")


def list_projects() -> list[dict]:
    """Summaries, most recently modified first."""
    rows = []
    for d in PROJECTS.iterdir():
        file = d / "project.json"
        if not d.is_dir() or not file.exists():
            continue
        proj = json.loads(file.read_text(encoding="utf-8"))
        pages = proj.get("pages", {})
        rows.append(
            {
                "id": d.name,
                "title": proj.get("title") or d.name,
                "pages": len(pages),
                "bubbles": sum(len(b) for b in pages.values()),
                "updated": file.stat().st_mtime,
            }
        )
    return sorted(rows, key=lambda r: -r["updated"])


def create_project(title: str) -> str:
    base = slugify(title)
    pid, n = base, 1
    while (PROJECTS / pid).exists():
        n += 1
        pid = f"{base}-{n}"
    (PROJECTS / pid / "pages").mkdir(parents=True)
    save_project(pid, empty_project(title))
    return pid


def delete_project(pid: str) -> None:
    shutil.rmtree(project_dir(pid))


def migrate_legacy() -> None:
    """Move the old single-project layout (data/project.json + data/pages/) into a project folder."""
    if not LEGACY_PROJECT_FILE.exists():
        return
    proj = json.loads(LEGACY_PROJECT_FILE.read_text(encoding="utf-8"))
    pid = create_project(proj.get("title") or "Imported project")
    if LEGACY_PAGES.is_dir():
        shutil.rmtree(PROJECTS / pid / "pages")
        shutil.move(str(LEGACY_PAGES), PROJECTS / pid / "pages")
    # Register images that were uploaded but are missing from the project's page list.
    proj.setdefault("pages", {})
    for f in (PROJECTS / pid / "pages").iterdir():
        if f.suffix.lower() in IMAGE_SUFFIXES:
            proj["pages"].setdefault(f.name, [])
    save_project(pid, proj)
    LEGACY_PROJECT_FILE.unlink()
