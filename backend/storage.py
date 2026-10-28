"""Project persistence (a single JSON file)."""
import json

from .config import PROJECT_FILE


def load_project() -> dict:
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    return {"title": "", "context": "", "glossary": [], "pages": {}}


def save_project(p: dict) -> None:
    PROJECT_FILE.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
