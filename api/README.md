# Crolo · API

FastAPI + SQLite backend for Crolo. It authenticates users, imports Anki
`.apkg` packages and serves generated multiple-choice quizzes.

## Requirements

- Python `3.10+` (the code uses `str | None` syntax)
- SQLite (bundled with Python)

## Setup

```bash
cd api

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

`zstandard` is only needed on Python < 3.14; newer versions use the standard
library `compression.zstd`.

## Environment

Create `api/.env` from the example:

```bash
cp .env.example .env
```

| Variable       | Required | Description                                                                 |
| -------------- | -------- | --------------------------------------------------------------------------- |
| `SECRET_KEY`   | Yes      | Secret used to sign JWTs. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `DATABASE_URL` | No       | SQLAlchemy URL. Defaults to `sqlite:///./crolo.db`.                          |

The app will fail to start if `SECRET_KEY` is missing.

## Database

The database is SQLite at `api/crolo.db` by default. Tables are created
automatically on import, including the deck and quiz tables.

Seed the default roles (`user`, `admin`, `moderator`):

```bash
python setup_db.py
```

To start from a clean database, delete `crolo.db` and run `setup_db.py` again.

## Run

```bash
source venv/bin/activate
uvicorn main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Bind to another host/port:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

### Auth

| Method | Path         | Auth   | Description                          |
| ------ | ------------ | ------ | ------------------------------------ |
| `GET`  | `/`          | No     | Health/welcome message               |
| `POST` | `/register/` | No     | Create a user (JSON)                 |
| `POST` | `/token`     | No     | OAuth2 password grant (form-encoded) |
| `GET`  | `/users/me`  | Bearer | Current user                         |
| `GET`  | `/protected` | Bearer | Sample protected route               |

Access tokens expire after 30 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES` in `auth.py`).

### Decks (all require a bearer token)

| Method   | Path                                      | Description                                   |
| -------- | ----------------------------------------- | --------------------------------------------- |
| `POST`   | `/decks/import`                           | Upload `.apkg` (multipart `file`)             |
| `GET`    | `/decks`                                  | List the current user's decks with statistics |
| `GET`    | `/decks/{id}`                             | Deck summary + full import report             |
| `PATCH`  | `/decks/{id}`                             | Rename                                        |
| `DELETE` | `/decks/{id}`                             | Delete deck and its sessions                  |
| `POST`   | `/decks/{id}/publish`                     | Draft → ready, required to start a quiz       |
| `GET`    | `/decks/{id}/items`                       | Paginated questions (`page`, `page_size`, `search`, `filter`) |
| `POST`   | `/decks/{id}/items`                       | Add a question by hand                        |
| `PATCH`  | `/decks/{id}/items`                       | Bulk save edits (`{"updates": [[id, patch], ...]}`) |
| `PATCH`  | `/decks/{id}/items/{itemId}`              | Edit one question                             |
| `DELETE` | `/decks/{id}/items/{itemId}`              | Delete one question                           |
| `POST`   | `/decks/{id}/items/{itemId}/regenerate`   | Rebuild its distractors                       |

`filter` accepts `all`, `ready`, `review`, `hidden`, `missing_meaning`.

### Quiz

| Method | Path                         | Description                                       |
| ------ | ---------------------------- | ------------------------------------------------- |
| `POST` | `/decks/{id}/sessions`       | Start a session (`mode`, `source`, `count`, `item_ids`) |
| `GET`  | `/sessions/{id}`             | Session state                                     |
| `POST` | `/sessions/{id}/answer`      | Submit one answer (instant mode)                  |
| `POST` | `/sessions/{id}/answers`     | Submit all answers at once (end mode)             |
| `POST` | `/sessions/{id}/finish`      | Finish and reveal results                         |

`mode` is `instant` or `end`; `source` is `all`, `unseen` or `weak`. The correct
answer is never sent to the client before it has been submitted.

## Anki import

`apkg/` implements the whole pipeline:

- `archive.py` — opens the ZIP, reads the protobuf `meta`, picks
  `collection.anki21b` (zstd, schema 18) or the legacy `collection.anki2` /
  `collection.anki21`, and ignores the "please upgrade Anki" stub that modern
  packages also contain.
- `sqlite_reader.py` — reads the database from memory, registers the `unicase`
  collation and clears the WAL flag so SQLite can open the file.
- `schema.py` — reads notetypes, fields, decks and notes for schema 11 and 18.
- `html_text.py` — strips Anki HTML and understands `<ruby>`, `漢字[かんじ]`,
  `[sound:]` and cloze syntax.
- `extract.py` — maps fields to prompt / reading / translation by name and by
  content, normalises katakana to hiragana and reports every skipped card.
- `distractors.py` — builds four options from realistic mis-readings (voicing,
  sokuon, long vowels, yo-on) plus readings from the same deck.
- `importer.py` — the end-to-end entry point used by the API.
- `cli.py` — `python -m apkg.cli deck.apkg [--json]` prints an import report.

Cards are skipped (with a reason) when the prompt has no kanji, the reading is
missing or not hiragana, or the card uses cloze syntax. Cards whose prompt has
several valid readings are imported but flagged `needs_review` and excluded from
quizzes until a reading is chosen in the editor.

## Tests

```bash
pytest
```

The suite uses the real packages in `tests/fixtures/`, synthetic schema-11 and
schema-18 collections, and an isolated temporary database.

## Notes

- CORS is not enabled. Use the web app's Vite proxy (`/api` → `http://127.0.0.1:8000`) or enable CORS in `main.py` if the client is on another origin.
- `venv/`, `__pycache__/`, `.env`, and `crolo.db` are ignored by Git.
- Uploads are capped at 100 MB; the decoded collection at 500 MB and 100,000 notes.
