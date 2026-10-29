"""Paths and environment configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent
BASE = BACKEND.parent
load_dotenv(BACKEND / ".env")

FRONTEND_DIST = BASE / "frontend" / "dist"
DATA = BASE / "data"
PROJECTS = DATA / "projects"  # one folder per project -> project.json + pages/
LEGACY_PROJECT_FILE = DATA / "project.json"
LEGACY_PAGES = DATA / "pages"

PROJECTS.mkdir(parents=True, exist_ok=True)

MODEL = os.environ.get("MANGA_ASSIST_MODEL", "claude-sonnet-5-5")

DETECTOR_REPO = "ogkalu/comic-text-and-bubble-detector"  # RT-DETR model. Classes: bubble / text_bubble / text_free
