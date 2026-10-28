"""Project persistence (a single JSON file)."""
import json
import re

from .config import PROJECT_FILE


def natural_key(name: str) -> list:
    """
    Sort key so that "2.jpg" comes before "10.jpg".
    """
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", name)]


def load_project() -> dict:
    if not PROJECT_FILE.exists():
        return {"title": "", "context": "", "glossary": [], "pages": {}}
    proj = json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    proj["pages"] = {k: proj["pages"][k] for k in sorted(proj.get("pages", {}), key=natural_key)}
    return proj


def save_project(p: dict) -> None:
    PROJECT_FILE.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
