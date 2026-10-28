"""Paths and environment configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env")

FRONTEND_DIST = BASE / "frontend" / "dist"
DATA = BASE / "data"
PAGES = DATA / "pages"
PROJECT_FILE = DATA / "project.json"

DATA.mkdir(exist_ok=True)
PAGES.mkdir(exist_ok=True)

MODEL = os.environ.get("MANGA_ASSIST_MODEL", "claude-sonnet-5-5")
