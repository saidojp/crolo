# Crolo

**Crolo** is an interactive Japanese-learning playground focused on **kanji
readings** and **vocabulary**. Its core workflow turns Anki decks (`.apkg`) into
automatically generated multiple-choice quizzes: you see a word in kanji and
pick the correct reading (furigana) from four hiragana options.

The project is a small full-stack application: a FastAPI backend that parses the
Anki package, extracts readings, generates distractors and stores progress, plus
a React single-page app for import, review and practice.

---

## Concept

Learning kanji readings is the hard part of Japanese vocabulary: the same
character can be read several ways, and similar-looking readings are easy to
confuse. Crolo tests exactly that skill:

- **Prompt** — a word written in kanji, e.g. `経済`
- **Options** — four hiragana readings, one correct (`けいざい`) and three
  plausible but wrong ones (`けざい`, `けいさい`, `けいざい` variants)
- **Translation** — shown only as a hint *after* answering, so it cannot give
  the reading away

Anki exports are the input format because most learners already have a deck.
Crolo does not try to replace Anki's scheduler; it is a separate practice mode
built on top of the same data.

---

## Features

- **One-click import** — drag an `.apkg`/`.colpkg` file, get a deck of questions.
- **Understanding import report** — how many notes were read, how many questions
  were generated, and why cards were skipped (no kanji, no reading, cloze, …).
- **Preview & editor** — inspect every generated question, fix the reading or
  translation, rewrite the answer options, hide or delete questions, add new
  ones by hand. Changes are saved to the server and apply to future sessions.
- **Two quiz modes**
  - *Instant feedback* — see correctness, the correct reading and the
    translation right after each answer.
  - *Answers at the end* — answer everything first, then review the whole run.
- **Question pools** — all questions, unseen questions, or weak ones (accuracy
  ≤ 70%), plus a session-length limit.
- **Results & retry** — score, per-question breakdown, and a one-click retry of
  just the mistakes.
- **Accounts** — decks and history are stored per user; a bearer JWT protects
  every deck and session endpoint.

---

## Tech stack

| Layer    | Technology                                                              |
| -------- | ----------------------------------------------------------------------- |
| Backend  | Python 3.10+, FastAPI, SQLAlchemy, SQLite, python-jose (JWT), passlib    |
| Parsing  | stdlib `zipfile`, `sqlite3` (in-memory), `html.parser`, protobuf reader  |
| Frontend | React 19, TypeScript, Vite 8, Chakra UI v3, React Router 7              |
| Tests    | pytest + httpx (API), Playwright (end-to-end)                           |

On Python < 3.14 the backend needs the `zstandard` package; newer versions use
the standard-library `compression.zstd`.

---

## Repository layout

```
api/                  FastAPI backend
  apkg/               .apkg parsing and quiz generation
    archive.py        ZIP, protobuf meta, zstd, collection selection
    sqlite_reader.py  in-memory SQLite, `unicase` collation, WAL fix
    schema.py         Anki schema 11 and 18 readers
    html_text.py      HTML / ruby / sound / cloze to plain text
    extract.py        field roles, reading extraction, import report
    distractors.py    distractor strategies and option validation
    importer.py       end-to-end import pipeline
    cli.py            `python -m apkg.cli deck.apkg`
  routers/            deck and quiz HTTP routes
  deck_crud.py        database operations for decks and sessions
  database.py         SQLAlchemy models
  main.py             app entry point, auth routes, /health
  tests/              pytest suite with real sample decks as fixtures
web/                  React front end
  src/pages/          Decks, deck editor, quiz, results
  src/components/     import report, question dialog, kanji typography
  e2e/                Playwright smoke tests
sample/               Two real Anki decks used for calibration
```

---

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

Open `http://localhost:5173`, create an account, go to **Decks**, and drop one of
the packages from `sample/`. You can also inspect a package without the UI:

```bash
cd api
python -m apkg.cli "../sample/JLPT N3 Vocab.apkg"
```

---

## How it works

### 1. Reading the Anki package

An `.apkg` is a ZIP archive. Modern packages (Anki 2.1.50+) contain:

| Entry                | Contents                                            |
| -------------------- | --------------------------------------------------- |
| `meta`               | protobuf `PackageMetadata` (format version)         |
| `collection.anki21b` | zstd-compressed SQLite database, schema 18          |
| `collection.anki2`   | a **stub** telling old Anki clients to upgrade      |
| `media`              | protobuf media index (not used in the MVP)          |

Legacy packages instead contain a plain `collection.anki2` or
`collection.anki21`. Crolo trusts `meta` to choose the file, so the stub is never
mistaken for the real database. The database is opened from memory; Anki's
`COLLATE unicase` collation is registered manually, and the WAL flag in the
SQLite header is cleared because the `-wal` sidecar does not exist inside the
archive.

Import limits: 100 MB archive, 500 MB decoded collection, 100,000 notes.

### 2. Finding the reading

Deck layouts differ, so field roles are resolved by name **and** content:

- name candidates: `Expression`/`Front`/`Word` for the prompt,
  `Reading`/`Furigana`/`Kana` for the reading,
  `Meaning`/`Translation`/`Back` for the translation;
- content fallback: the field with the highest kanji density becomes the prompt;
- `Back` is treated as a *combined* field and split into reading + translation.

Supported reading shapes:

```
Reading field:      さほう
Inline:             けいざい экономика
Two lines:          けいざい<br>экономика
Anki ruby:          経済[けいざい] экономика
HTML ruby:          <ruby>経済<rt>けいざい</rt></ruby>
```

Readings are normalised (NFKC, katakana → hiragana, whitespace and trailing
qualifiers removed) and must contain only hiragana plus the long-vowel mark.
A prompt must contain at least one kanji, otherwise the card is skipped — a
kana-only word would make the quiz trivial.

### 3. Generating distractors

Every question gets four options:

- **Strategy A — realistic mis-readings** of the correct answer: voicing
  (`さ → ざ`), handakuten (`は → ぱ`), sokuon insertion/removal (`はっき → はき`),
  long-vowel collapse (`さほう → さほ`), yo-on contraction (`きょ ↔ きよ`),
  small/large kana confusion.
- **Strategy B — the deck pool**: readings of other words from the same deck,
  preferring similar length and shared morae.

Options never include another *valid* reading of the same prompt, are always
unique, and the correct one is stored separately so it can be checked on the
server. Generation is deterministic per question (a stable hash of prompt +
reading), so the same import produces the same quiz.

### 4. Review before practising

The editor exposes everything the parser inferred. Questions whose prompt has
several valid readings (`上 → かみ / じょう / うわ`) are imported but flagged
`needs_review` and excluded from quizzes until the learner picks one. A deck must
be published before a session can start.

### 5. Answering safely

Options and the correct index are copied into the session when it starts, so
editing the deck later cannot break an active quiz. The API never sends
`correct_index` before an answer is submitted:

- *instant* — one `POST /sessions/{id}/answer` per question, the response
  reveals correctness, reading and translation;
- *end* — answers are buffered client-side and sent as one batch, and results
  are only revealed by `POST /sessions/{id}/finish`.

---

## Data model

| Table                | Purpose                                                        |
| -------------------- | -------------------------------------------------------------- |
| `users`, `roles`     | accounts and role assignments                                   |
| `decks`              | imported deck, owner, source file, import report, status        |
| `deck_items`         | one question: prompt, reading, translation, options, flags      |
| `quiz_sessions`      | a practice run: mode, source pool, totals, timestamps           |
| `quiz_session_items` | snapshot of each question and the user's answer                 |

Statistics (accuracy, sessions completed, last played) are derived from finished
sessions; "weak" and "unseen" pools are computed from the same history.

---

## API overview

All deck and quiz routes require `Authorization: Bearer <token>`.

| Method   | Path                                     | Purpose                          |
| -------- | ---------------------------------------- | -------------------------------- |
| `POST`   | `/register/`, `/token`                   | sign up / sign in                |
| `GET`    | `/health`                                | liveness + database probe        |
| `POST`   | `/decks/import`                          | upload `.apkg` (multipart)       |
| `GET`    | `/decks`, `/decks/{id}`                  | list decks / deck + report       |
| `PATCH`  | `/decks/{id}`                            | rename                           |
| `DELETE` | `/decks/{id}`                            | delete deck and history          |
| `POST`   | `/decks/{id}/publish`                    | make a deck playable             |
| `GET`    | `/decks/{id}/items`                      | paginated, searchable questions  |
| `POST`   | `/decks/{id}/items`                      | add a question manually          |
| `PATCH`  | `/decks/{id}/items`                      | bulk save edits                  |
| `PATCH`  | `/decks/{id}/items/{itemId}`             | edit one question                |
| `DELETE` | `/decks/{id}/items/{itemId}`             | delete one question              |
| `POST`   | `/decks/{id}/items/{itemId}/regenerate`  | rebuild its distractors          |
| `POST`   | `/decks/{id}/sessions`                   | start a quiz                     |
| `POST`   | `/sessions/{id}/answer`                  | submit one answer (instant)      |
| `POST`   | `/sessions/{id}/answers`                 | submit all answers (end)         |
| `POST`   | `/sessions/{id}/finish`                  | finish and reveal results        |
| `GET`    | `/sessions/{id}`                         | session state and results        |

`GET /decks/{id}/items` accepts `page`, `page_size`, `search`, and `filter`
(`all`, `ready`, `review`, `hidden`, `missing_meaning`).

---

## Screens

| Route                       | Purpose                                              |
| --------------------------- | ---------------------------------------------------- |
| `/decks`                    | Import, import report, deck list with statistics     |
| `/decks/:id`                | Preview / editor, filters, save, publish             |
| `/decks/:id/quiz`           | Session setup and quiz runner (keyboard 1–4, Enter)  |
| `/sessions/:id/results`     | Score, per-question review, retry mistakes           |

The interface language is English; the design follows the existing dark Chakra
theme.

---

## Validation on real decks

Both packages in `sample/` are used as test fixtures:

| Deck                    | Notes | Questions | Quiz-ready | Skipped                          |
| ----------------------- | ----: | --------: | ---------: | -------------------------------- |
| `JLPT N3 Vocab.apkg`    |  2139 |      1896 |       1823 | 242 kana-only prompts, 1 bad reading |
| `10月20日.apkg`          |    16 |        15 |         15 | 1 kana-only prompt                |

The JLPT deck uses a dedicated `Expression` / `Reading` / `Meaning` notetype; the
second one uses `Front` / `Back` where `Back` holds the reading (and sometimes a
Russian example sentence). 36 JLPT words have several valid readings
(73 cards), which is why they are flagged rather than guessed.

---

## Testing

```bash
cd api && pytest                  # 85 tests: parser, API, ownership, quiz modes
cd web && npm run test:e2e        # 4 Playwright smoke tests
```

The backend suite covers schema 11 and 18 packages, zstd decoding, the upgrade
stub, HTML/ruby/cloze parsing, ambiguous readings, distractor invariants,
authorization, editing rules, and both quiz modes. The end-to-end suite drives a
real browser through import → edit → publish → quiz → results.

---

## Limitations and non-goals

- No audio or images from Anki media; cards are text-only.
- No SRS scheduling or Anki sync — Crolo is a practice mode, not a replacement.
- Only multiple-choice reading questions; no typed input.
- Cloze notetypes are skipped.
- Re-importing creates a *new* deck; there is no merge by note GUID yet.
- No deck sharing or collaborative editing.

---

## Roadmap

- Re-import into an existing deck with GUID-based merge.
- Keyboard-typed answers and listening questions using deck audio.
- Per-card history charts and spaced repetition built on top of the session log.
- Additional exercise types (kanji → meaning, meaning → kanji).
- Shared/public decks.

---

See `api/README.md` for endpoint and parsing details, and `web/README.md` for
front-end scripts, environment variables and Playwright setup.
