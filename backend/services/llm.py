"""Anthropic client and the draft/check prompt."""
import json
import os

from fastapi import HTTPException

from ..config import MODEL
from ..schemas import DraftReq

_client = None

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


def get_client():
    global _client
    if _client is None:
        import anthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(500, "ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic()
    return _client


def build_prompt(req: DraftReq) -> str:
    gloss = "\n".join(
        f"- {g.get('ja','')} = {g.get('en','')}" + (f" ({g['note']})" if g.get("note") else "")
        for g in req.glossary
    ) or "(none)"
    return (
        f"Series/chapter context:\n{req.context or '(none)'}\n\n"
        f"Glossary:\n{gloss}\n\n"
        f"Neighboring bubbles (Japanese, reading order):\n"
        + ("\n".join(f"- {n}" for n in req.neighbors) or "(none)")
        + f"\n\nBubble to translate:\n{req.ja}\n\n"
        f"Translator's draft (may be empty):\n{req.draft or '(none)'}"
    )


def parse_reply(text: str) -> dict:
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"literal": "", "suggestion": text, "notes": "model returned non-JSON", "flags": []}


def draft(req: DraftReq) -> dict:
    msg = get_client().messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(req)}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    return parse_reply(text)
