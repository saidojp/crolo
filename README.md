# Crolo

An interactive playground for learning Japanese, focused on kanji readings and
vocabulary. Import an Anki deck (`.apkg`), review the generated questions, and
practise with multiple-choice reading quizzes.

## Repository layout

```
api/   FastAPI + SQLite backend (auth, .apkg import, quiz engine)
web/   React + Chakra UI front end
sample/  Two real Anki decks used for calibration
```

## Quick start

```bash
# API
cd api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then set SECRET_KEY
python setup_db.py
uvicorn main:app --reload       # http://127.0.0.1:8000

# Web (second terminal)
cd web
npm install
npm run dev                     # http://localhost:5173
```

## How it works

1. **Import** — upload an `.apkg` on `/decks`. The backend unzips the package,
   decodes the protobuf `meta`, reads the zstd-compressed `collection.anki21b`
   (or the legacy `collection.anki2`), and extracts prompt / reading /
   translation from Anki notes.
2. **Generate** — each note becomes a question with four hiragana options:
   realistic mis-readings (voicing, sokuon, long vowels, yo-on) plus readings of
   other words from the same deck.
3. **Review** — `/decks/:id` shows an import report and an editable table. Fix a
   reading, rewrite options, hide or delete a question, then save.
4. **Quiz** — `/decks/:id/quiz` offers *instant feedback* or *answers at the end*,
   with `all` / `unseen` / `weak` question pools. The correct answer is only sent
   after submission.
5. **Results** — score, per-question review, and *retry mistakes*.

Cards with no kanji in the prompt, no hiragana reading, or cloze syntax are
skipped with a reason shown in the import report. Prompts with several valid
readings are imported but flagged for review and excluded from quizzes until a
decision is made.

## Tests

```bash
cd api && pytest                        # parser, API, ownership, quiz modes
cd web && npm run test:e2e              # Playwright smoke tests
```

See `api/README.md` and `web/README.md` for details on endpoints, environment
variables and the parsing pipeline.
