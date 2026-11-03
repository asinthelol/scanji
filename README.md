# Scanji

A local tool for drafting and proofreading Japanese to English manga translations. Detect the bubbles on a page, OCR them, write your own draft, and let Claude check it and suggest a natural line. Then export a plain script for your typesetting tools.

## Quick Start

### Local Development

1. Clone the repo

```bash
git clone https://github.com/asinthelol/manga-assist.git scanji
cd scanji
```

2. Install the backend dependencies

```bash
python -m venv backend/.venv
backend/.venv/Scripts/activate        # macOS/Linux: source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

3. Add your Anthropic API key

```bash
cp backend/.env.example backend/.env
```

Then put your key in `backend/.env` (`ANTHROPIC_API_KEY=...`).

4. Build the frontend

```bash
cd frontend
npm install
npm run build
```

5. Run the app

```bash
cd ..
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000.

For frontend work, run `npm run dev` in `frontend/` as well and open http://localhost:5173 instead. It proxies `/api` to the backend.

The first OCR and bubble detection run download their models (manga-ocr and an RT-DETR detector), so expect a wait the first time. The first time you open the dictionary it downloads JMdict (about 12 MB) and indexes it into `data/dictionary/` (about 100 MB), which takes around 15 seconds. After that, lookups work offline.

## How To Use

1. Add a project on the home page, one per series
2. Add a chapter with the **+** in the navbar, then **Add pages** to upload its images
3. Click **Detect bubbles**, or drag on the page to box a bubble yourself. Each box is OCR'd automatically
4. Fix the Japanese if OCR got it wrong, then write your own draft
5. Hit **Draft / Check** to get a literal gloss, a natural suggestion, notes, and flags on your draft
6. **Use** the suggestion or edit the **Final** line. Drag the grip handle to reorder bubbles, or **Sort order** to reset to reading order
7. **Export script** downloads the chapter as a markdown file

The **Dictionary** button in the navbar opens a lookup panel beside the cards. Search by Japanese, reading, or English. Conjugated forms like 食べた find their dictionary form.

## Features

- Bubble detection with a manga-specific model, plus manually-drawn boxes
- Reading-order sorting (right-to-left, top-to-bottom) and drag-to-reorder
- OCR with manga-ocr, running locally (takes ~10s to load on first detect)
- Drafting and proofreading through the Anthropic API that respects your glossary, series context, and the surrounding bubbles
- Offline JMdict dictionary panel, with fallbacks for conjugated words
- Projects with chapters; the glossary and context are shared across a project's chapters
- Plain-line script export with customizable headings (`{title}`, `{chapter}`, `{page}`)
- Autosave to disk
- Backend test suite (pytest, with OCR, Anthropic, and the detector mocked)

## Prerequisites

- **Python** 3.10+ for the backend
- **Node.js** to build the frontend
- **An Anthropic API key** for Draft / Check. Detection, OCR, and the rest work without one
- Several GB of disk for PyTorch and the two models.

Only the Japanese text, your draft, the glossary, and the series context are sent to Anthropic.

## Configuration

Set in `backend/.env`:

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Required for Draft / Check |
| `SCANJI_MODEL` | Optional model override for drafting |

Your projects live in `data/` (git-ignored): one folder per project with a `project.json` and its pages.

## Running Tests

```bash
pip install -r backend/requirements-dev.txt
pytest
```

## Built With

- **Backend**: FastAPI, Pillow, manga-ocr, Hugging Face Transformers (RT-DETR detector), SQLite
- **Dictionary data**: [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) via [jmdict-simplified](https://github.com/scriptin/jmdict-simplified)
- **Frontend**: React, TypeScript, Vite, Tailwind, shadcn/ui, dnd-kit
- **Drafting**: Anthropic API

## License

I don't care what you do with it, just don't say you made this.

---

### by asinthelol
