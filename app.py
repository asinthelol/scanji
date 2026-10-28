"""
manga-assist: tool for drafting and proofreading manga translations (JA -> EN).

Run:  uvicorn app:app --reload
Config (via .env):
  ANTHROPIC_API_KEY   needed for AI drafting/proofreading
  MANGA_ASSIST_MODEL  optional model override
"""
import io
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
PAGES = DATA / "pages"
PAGES.mkdir(exist_ok=True)
PROJECT_FILE = DATA / "project.json"

MODEL = os.environ.get("MANGA_ASSIST_MODEL", "claude-sonnet-5-5")

app = FastAPI(title="manga-assist")

# ---------- lazy singletons ----------
_ocr = None
_client = None


def get_ocr():
    global _ocr
    if _ocr is None:
        from manga_ocr import MangaOcr  # heavy import, load on first use

        _ocr = MangaOcr()
    return _ocr


def get_client():
    global _client
    if _client is None:
        import anthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(500, "ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic()
    return _client


# ---------- project storage ----------
def load_project() -> dict:
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    return {"title": "", "context": "", "glossary": [], "pages": {}}


def save_project(p: dict) -> None:
    PROJECT_FILE.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")


class Box(BaseModel):
    id: str
    x: float
    y: float
    w: float
    h: float
    ja: str = ""
    draft: str = ""          # User's draft
    suggestion: str = ""     # model's natural-English suggestion
    literal: str = ""        # model's literal gloss
    notes: str = ""          # model's notes / flags
    final: str = ""


class Project(BaseModel):
    title: str = ""
    context: str = ""          # series/chapter context: characters, tone, setting
    glossary: list[dict] = []  # [{"ja": "...", "en": "...", "note": "..."}]
    pages: dict[str, list[Box]] = {}


# ---------- routes ----------
@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/api/project")
def get_project():
    return load_project()


@app.put("/api/project")
def put_project(p: Project):
    save_project(json.loads(p.model_dump_json()))
    return {"ok": True}


@app.post("/api/pages")
async def upload_page(file: UploadFile = File(...)):
    name = Path(file.filename or "page.png").name
    raw = await file.read()
    
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except Exception:
        raise HTTPException(400, "Not a valid image")
    
    (PAGES / name).write_bytes(raw)
    proj = load_project()
    proj["pages"].setdefault(name, [])
    save_project(proj)
    
    return {"name": name}


@app.get("/api/pages/{name}")
def get_page(name: str):
    path = PAGES / Path(name).name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


class OcrReq(BaseModel):
    page: str
    x: float
    y: float
    w: float
    h: float  # all in image pixels


@app.post("/api/ocr")
def ocr_region(req: OcrReq):
    path = PAGES / Path(req.page).name
    if not path.exists():
        raise HTTPException(404, "page not found")
    
    img = Image.open(path).convert("RGB")
    box = (int(req.x), int(req.y), int(req.x + req.w), int(req.y + req.h))
    crop = img.crop(box)
    if crop.width < 4 or crop.height < 4:
        raise HTTPException(400, "region too small")
    
    text = get_ocr()(crop)
    return {"ja": text}


class DraftReq(BaseModel):
    ja: str
    draft: str = ""
    context: str = ""
    glossary: list[dict] = []
    neighbors: list[str] = []  # Japanese text of surrounding bubbles, in reading order


SYSTEM = """
You are a Japanese-to-English manga translation assistant for a translator.
You see one speech bubble at a time, plus nearby bubbles for context.
Return ONLY a JSON object with keys:
  "literal": a faithful, word-for-word-ish gloss (keep it clunky; this is for checking meaning),
  "suggestion": natural, concise English suited to a speech bubble (match the speaker's tone),
  "notes": short notes on nuance, honorifics, wordplay, ambiguity, or anything the translator should double-check,
  "flags": a list of problems in the translator's draft if one was provided (mistranslation, omitted meaning, too literal, tone mismatch, typo/grammar), or an empty list if none or no draft.
Respect the glossary exactly. Do not invent context you cannot see; say so in notes if the line is ambiguous.
"""


@app.post("/api/draft")
def draft(req: DraftReq):
    gloss = "\n".join(
        f"- {g.get('ja','')} = {g.get('en','')}" + (f" ({g['note']})" if g.get("note") else "")
        for g in req.glossary
    ) or "(none)"
    user = (
        f"Series/chapter context:\n{req.context or '(none)'}\n\n"
        f"Glossary:\n{gloss}\n\n"
        f"Neighboring bubbles (Japanese, reading order):\n"
        + ("\n".join(f"- {n}" for n in req.neighbors) or "(none)")
        + f"\n\nBubble to translate:\n{req.ja}\n\n"
        f"Translator's draft (may be empty):\n{req.draft or '(none)'}"
    )
    msg = get_client().messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"literal": "", "suggestion": text, "notes": "model returned non-JSON", "flags": []}
    return data


@app.get("/api/export", response_class=PlainTextResponse)
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


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
