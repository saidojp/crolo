"""Read notes, notetypes and decks out of an Anki collection.

Supports schema 18 (Anki 2.1.50+) and the legacy schema 11 that older
``collection.anki2`` files still use.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from apkg.errors import ApkgError

SUPPORTED_MIN_SCHEMA = 11
SUPPORTED_MAX_SCHEMA = 18
DEFAULT_MAX_NOTES = 100_000

FIELD_SEPARATOR = "\x1f"
DECK_SEPARATOR = "\x1f"

# Anki's built-in deck is called "Default" in English builds, but the name is
# localised, so we only prefer other decks and fall back if it is all we have.
DEFAULT_DECK_NAMES = {"default", "по умолчанию"}


@dataclass(frozen=True)
class Notetype:
    id: int
    name: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class Deck:
    id: int
    name: str


@dataclass(frozen=True)
class Note:
    id: int
    notetype_id: int
    fields: tuple[str, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Card:
    note_id: int
    deck_id: int


@dataclass
class Collection:
    schema_version: int
    notetypes: dict[int, Notetype]
    decks: dict[int, Deck]
    notes: list[Note]
    cards: list[Card]
    deck_id: int | None = None
    deck_name: str = ""
    export_version: int | None = None
    extra: dict[str, object] = field(default_factory=dict)

    def notetype_for(self, note: Note) -> Notetype | None:
        return self.notetypes.get(note.notetype_id)


def read_collection(con: sqlite3.Connection, *, max_notes: int = DEFAULT_MAX_NOTES) -> Collection:
    try:
        row = con.execute("SELECT ver FROM col").fetchone()
    except sqlite3.DatabaseError as exc:
        raise ApkgError("corrupt_collection", f"The collection table is unreadable: {exc}")

    if row is None:
        raise ApkgError("corrupt_collection", "The collection has no metadata row")

    schema_version = int(row[0])
    if schema_version < SUPPORTED_MIN_SCHEMA:
        raise ApkgError(
            "unsupported_version",
            f"Collection schema {schema_version} is older than the supported minimum",
        )
    if schema_version > SUPPORTED_MAX_SCHEMA:
        raise ApkgError(
            "unsupported_version",
            f"Collection schema {schema_version} was created by a newer version of Anki",
        )

    if schema_version >= 15:
        notetypes = _read_notetypes_v18(con)
        decks = _read_decks_v18(con)
    else:
        models, legacy_decks = _read_legacy_json(con)
        notetypes = _notetypes_from_models(models)
        decks = _decks_from_json(legacy_decks)

    notes = _read_notes(con, notetypes, max_notes=max_notes)
    cards = _read_cards(con)
    deck_id, deck_name = _pick_deck(decks, cards, notes)

    return Collection(
        schema_version=schema_version,
        notetypes=notetypes,
        decks=decks,
        notes=notes,
        cards=cards,
        deck_id=deck_id,
        deck_name=deck_name,
    )


def _read_notetypes_v18(con: sqlite3.Connection) -> dict[int, Notetype]:
    try:
        rows = con.execute("SELECT id, name FROM notetypes").fetchall()
        field_rows = con.execute(
            "SELECT ntid, ord, name FROM fields ORDER BY ntid, ord"
        ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise ApkgError("corrupt_collection", f"Could not read notetypes: {exc}")

    fields_by_type: dict[int, list[tuple[int, str]]] = {}
    for ntid, ordinal, name in field_rows:
        fields_by_type.setdefault(int(ntid), []).append((int(ordinal), str(name)))

    notetypes: dict[int, Notetype] = {}
    for ntid, name in rows:
        ordered = sorted(fields_by_type.get(int(ntid), []))
        notetypes[int(ntid)] = Notetype(
            id=int(ntid),
            name=str(name),
            fields=tuple(field_name for _, field_name in ordered),
        )
    return notetypes


def _read_decks_v18(con: sqlite3.Connection) -> dict[int, Deck]:
    try:
        rows = con.execute("SELECT id, name FROM decks").fetchall()
    except sqlite3.DatabaseError as exc:
        raise ApkgError("corrupt_collection", f"Could not read decks: {exc}")
    return {int(did): Deck(id=int(did), name=_human_deck_name(str(name))) for did, name in rows}


def _read_legacy_json(con: sqlite3.Connection) -> tuple[dict, dict]:
    try:
        row = con.execute("SELECT models, decks FROM col").fetchone()
    except sqlite3.DatabaseError as exc:
        raise ApkgError("corrupt_collection", f"Could not read legacy collection: {exc}")
    if row is None:
        return {}, {}
    try:
        models = json.loads(row[0] or "{}")
        decks = json.loads(row[1] or "{}")
    except (TypeError, ValueError) as exc:
        raise ApkgError("corrupt_collection", f"Invalid legacy metadata: {exc}")
    return models, decks


def _notetypes_from_models(models: dict) -> dict[int, Notetype]:
    result: dict[int, Notetype] = {}
    for key, model in models.items():
        try:
            ntid = int(model.get("id", key))
        except (TypeError, ValueError):
            continue
        fields = [
            str(item.get("name", ""))
            for item in sorted(model.get("flds", []), key=lambda item: int(item.get("ord", 0)))
        ]
        result[ntid] = Notetype(id=ntid, name=str(model.get("name", f"Model {ntid}")), fields=tuple(fields))
    return result


def _decks_from_json(decks: dict) -> dict[int, Deck]:
    result: dict[int, Deck] = {}
    for key, deck in decks.items():
        try:
            did = int(deck.get("id", key))
        except (TypeError, ValueError):
            continue
        result[did] = Deck(id=did, name=_human_deck_name(str(deck.get("name", f"Deck {did}"))))
    return result


def _human_deck_name(name: str) -> str:
    return name.replace(DECK_SEPARATOR, "::").strip()


def _read_notes(
    con: sqlite3.Connection,
    notetypes: dict[int, Notetype],
    *,
    max_notes: int,
) -> list[Note]:
    try:
        total = int(con.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        raise ApkgError("corrupt_collection", f"Could not count notes: {exc}")
    if total > max_notes:
        raise ApkgError(
            "too_many_notes",
            f"The collection has {total:,} notes; the limit is {max_notes:,}",
        )

    try:
        rows = con.execute("SELECT id, mid, flds, tags FROM notes ORDER BY id").fetchall()
    except sqlite3.DatabaseError as exc:
        raise ApkgError("corrupt_collection", f"Could not read notes: {exc}")

    notes: list[Note] = []
    for note_id, mid, flds, tags in rows:
        note = Note(
            id=int(note_id),
            notetype_id=int(mid),
            fields=tuple(str(flds).split(FIELD_SEPARATOR)),
            tags=tuple(str(tags or "").split()),
        )
        notes.append(note)
    return notes


def _read_cards(con: sqlite3.Connection) -> list[Card]:
    try:
        rows = con.execute("SELECT nid, did FROM cards").fetchall()
    except sqlite3.DatabaseError:
        # A notes-only export is unusual but harmless; deck selection falls
        # back to the deck list.
        return []
    return [Card(note_id=int(nid), deck_id=int(did)) for nid, did in rows]


def _pick_deck(
    decks: dict[int, Deck],
    cards: list[Card],
    notes: list[Note],
) -> tuple[int | None, str]:
    if not decks:
        return None, ""

    note_ids = {note.id for note in notes}
    counts: Counter[int] = Counter()
    for card in cards:
        if card.note_id in note_ids:
            counts[card.deck_id] += 1

    if not counts:
        return min(decks), decks[min(decks)].name

    def score(item: tuple[int, int]) -> tuple[int, int]:
        deck_id, count = item
        deck = decks.get(deck_id)
        is_default = deck is not None and deck.name.casefold() in DEFAULT_DECK_NAMES
        return (0 if is_default else 1, count)

    deck_id = max(counts.items(), key=score)[0]
    name = decks.get(deck_id)
    return deck_id, name.name if name else f"Deck {deck_id}"
