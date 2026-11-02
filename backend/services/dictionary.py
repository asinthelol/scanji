"""
Offline Japanese-English dictionary (JMdict).

The data is JMdict-simplified's English release. It downloads once into data/dictionary/ and is
indexed into SQLite, which takes a few seconds. Lookups never touch the network.
"""
import io
import json
import os
import sqlite3
import threading
import unicodedata
import urllib.request
import zipfile
from contextlib import closing
from pathlib import Path

from ..config import DATA

RELEASES_API = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"
DB_PATH = DATA / "dictionary" / "jmdict.db"
MAX_ENTRIES = 30
MIN_STEM = 2  # shortest leading part tried when a Japanese word has no entry of its own
DICTIONARY_FORM_ENDINGS = "うくぐすつぬぶむるい"  # 食べ -> 食べる, 行か -> 行く, 高かっ -> 高い

SCHEMA = """
CREATE TABLE entries (id INTEGER PRIMARY KEY, common INTEGER NOT NULL, data TEXT NOT NULL);
-- form: 1 for kanji and readings, 0 for glosses. weight: 0 for forms and the first sense's glosses, 1 for the rest.
CREATE TABLE terms (text TEXT NOT NULL, entry_id INTEGER NOT NULL, form INTEGER NOT NULL, weight INTEGER NOT NULL);
CREATE INDEX terms_text ON terms (text);
"""

_lock = threading.Lock()
_state = {"status": "missing", "message": ""}  # missing | downloading | indexing | ready | error


def normalize(text: str) -> str:
    """
    Fold width, case and katakana so コーヒー, こーひー and ｺｰﾋｰ search alike.
    """
    text = unicodedata.normalize("NFKC", text).strip().lower()
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def _terms(word: dict) -> dict[str, tuple[int, int]]:
    """
    Searchable text -> (form, weight), keeping the best weight when a text occurs more than once.
    """
    terms: dict[str, tuple[int, int]] = {}

    def add(text: str, form: int, weight: int) -> None:
        if text not in terms or weight < terms[text][1]:
            terms[text] = (form, weight)

    for f in word.get("kanji", []) + word.get("kana", []):
        add(normalize(f["text"]), 1, 0)
    for i, sense in enumerate(word["sense"]):
        for gloss in sense["gloss"]:
            text = normalize(gloss["text"])
            add(text, 0, min(i, 1))
            if text.startswith("to "):  # "to drink" should also be found by "drink"
                add(text[3:], 0, min(i, 1))
    return terms


def build_db(data: dict, path: Path) -> None:
    """
    Index a parsed JMdict-simplified file.
    """
    tags = data["tags"]
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    with closing(sqlite3.connect(partial)) as db:
        db.executescript(SCHEMA)
        for word in data["words"]:
            entry = {
                "kanji": [f["text"] for f in word.get("kanji", [])],
                "kana": [f["text"] for f in word.get("kana", [])],
                "senses": [
                    {"pos": [tags.get(p, p) for p in s["partOfSpeech"]], "gloss": [g["text"] for g in s["gloss"]]}
                    for s in word["sense"]
                ],
            }
            common = any(f.get("common") for f in word.get("kanji", []) + word.get("kana", []))
            db.execute("INSERT INTO entries VALUES (?, ?, ?)", (int(word["id"]), int(common), json.dumps(entry, ensure_ascii=False)))
            db.executemany(
                "INSERT INTO terms VALUES (?, ?, ?, ?)",
                [(text, int(word["id"]), form, weight) for text, (form, weight) in _terms(word).items()],
            )
        db.commit()
    os.replace(partial, path)


def _download_latest() -> dict:
    headers = {"User-Agent": "scanji"}  # GitHub rejects requests without one
    with urllib.request.urlopen(urllib.request.Request(RELEASES_API, headers=headers)) as res:
        assets = json.load(res)["assets"]
    asset = next(a for a in assets if a["name"].startswith("jmdict-eng-") and a["name"].endswith(".json.zip"))
    with urllib.request.urlopen(urllib.request.Request(asset["browser_download_url"], headers=headers)) as res:
        archive = zipfile.ZipFile(io.BytesIO(res.read()))
    return json.loads(archive.read(archive.namelist()[0]))


def _prepare() -> None:
    try:
        _state.update(status="downloading", message="Downloading the dictionary (about 12 MB, first run only)")
        data = _download_latest()
        _state.update(status="indexing", message="Indexing the dictionary")
        build_db(data, DB_PATH)
        _state.update(status="ready", message="")
    except Exception as e:  # network down, release layout changed, disk full...
        _state.update(status="error", message=f"Could not set up the dictionary: {e}")


def status() -> dict:
    """
    Current state, starting the one-time download in the background when there is no data yet.
    """
    with _lock:
        if DB_PATH.exists():
            _state.update(status="ready", message="")
        elif _state["status"] in ("missing", "error"):
            _state.update(status="downloading", message="Starting the dictionary download")
            threading.Thread(target=_prepare, daemon=True).start()
        return dict(_state)


def _search(db: sqlite3.Connection, q: str, exact: bool = False, forms_only: bool = False) -> list[int]:
    """
    Entry ids whose kanji, reading or gloss starts with q (equals q if `exact`). Exact matches come
    first, then ones in an entry's first sense, then common words, then shorter (closer) terms.
    """
    rows = db.execute(
        f"""
        SELECT t.entry_id
        FROM terms t JOIN entries e ON e.id = t.entry_id
        WHERE {"t.text = ?1" if exact else "t.text >= ?1 AND t.text < ?1 || char(1114111)"}
          AND (?3 = 0 OR t.form = 1)
        GROUP BY t.entry_id
        ORDER BY MIN((t.text != ?1) * 2 + t.weight), e.common DESC, MIN(length(t.text)), e.id
        LIMIT ?2
        """,
        (q, MAX_ENTRIES, int(forms_only)),
    )
    return [r[0] for r in rows]


def _dictionary_forms(db: sqlite3.Connection, q: str) -> tuple[str, list[int]]:
    """
    Entries for the dictionary form of an inflected word.
    The longest leading part of q that becomes a headword
    when a verb or adjective ending is added.
    """
    for n in range(len(q) - 1, 0, -1):
        ids = {i for e in DICTIONARY_FORM_ENDINGS for i in _search(db, q[:n] + e, exact=True, forms_only=True)}
        if ids:
            rows = db.execute(
                f"SELECT id FROM entries WHERE id IN ({','.join('?' * len(ids))}) ORDER BY common DESC, id", tuple(ids)
            )
            return q[:n], [r[0] for r in rows]
    return "", []


def _stem_hits(db: sqlite3.Connection, q: str) -> tuple[str, list[int]]:
    """
    The longest leading part of q (at least MIN_STEM characters) that has entries, with them.
    """
    for n in range(len(q) - 1, MIN_STEM - 1, -1):
        ids = _search(db, q[:n])
        if ids:
            return q[:n], ids
    return "", []


def lookup(query: str) -> dict:
    """
    Entries for a word, reading or English gloss. A Japanese word with no entry of its own is
    usually conjugated, so then `fallback` says what was found instead: "inflection" (the dictionary
    forms of `stem`) or "prefix" (words starting with `stem`).
    """
    q = normalize(query)
    state = status()
    if state["status"] != "ready" or not q:
        return {**state, "entries": [], "stem": "", "fallback": ""}

    with closing(sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)) as db:
        ids, stem, fallback = _search(db, q), "", ""
        if not ids and not q.isascii():
            for fallback, find in (("inflection", _dictionary_forms), ("prefix", _stem_hits)):
                stem, ids = find(db, q)
                if ids:
                    break
            else:
                fallback = ""
        entries = []
        for entry_id in ids:
            data, common = db.execute("SELECT data, common FROM entries WHERE id = ?", (entry_id,)).fetchone()
            entries.append({"id": entry_id, "common": bool(common), **json.loads(data)})
    return {**state, "entries": entries, "stem": stem, "fallback": fallback}
