"""Pydantic request/response models."""
from pydantic import BaseModel


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
    notes: str = ""          # model's notes on nuance and ambiguity
    flags: list[str] = []    # model's problems found in the user's draft
    final: str = ""


class Project(BaseModel):
    title: str = ""
    context: str = ""          # series/chapter context: characters, tone, setting
    glossary: list[dict] = []  # [{"ja": "...", "en": "...", "note": "..."}]
    pages: dict[str, list[Box]] = {}


class OcrReq(BaseModel):
    page: str
    x: float
    y: float
    w: float
    h: float  # all in image pixels


class DraftReq(BaseModel):
    ja: str
    draft: str = ""
    context: str = ""
    glossary: list[dict] = []
    neighbors: list[str] = []  # Japanese text of surrounding bubbles, in reading order
