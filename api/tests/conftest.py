"""Shared fixtures: real packages from the user's decks plus tiny builders."""

from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
# The same packages live in the repository's `sample/` folder; prefer the local
# copies when present and fall back to the repository-level samples otherwise.
REPO_SAMPLES = Path(__file__).resolve().parents[2] / "sample"


def _fixture(name: str) -> Path:
    local = FIXTURES / name
    return local if local.exists() else REPO_SAMPLES / name


JLPT_APKG = _fixture("JLPT N3 Vocab.apkg")
RUSSIAN_APKG = _fixture("10月20日.apkg")


@pytest.fixture(scope="session")
def jlpt_bytes() -> bytes:
    return JLPT_APKG.read_bytes()


@pytest.fixture(scope="session")
def russian_bytes() -> bytes:
    return RUSSIAN_APKG.read_bytes()


def build_sqlite(statements: list[str]) -> bytes:
    con = sqlite3.connect(":memory:")
    con.create_collation(
        "unicase",
        lambda left, right: (left.casefold() > right.casefold())
        - (left.casefold() < right.casefold()),
    )
    try:
        for statement in statements:
            con.execute(statement)
        con.commit()
        data = bytearray(con.serialize())
    finally:
        con.close()
    # Mark rollback-journal mode, like Anki's exported packages.
    data[18] = 1
    data[19] = 1
    return bytes(data)


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def package_meta(version: int = 3) -> bytes:
    return b"\x08" + _varint(version)


def build_apkg(
    db_bytes: bytes,
    *,
    version: int | None = 3,
    filename: str = "collection.anki21b",
    compress: bool = False,
    media_entries: int = 0,
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if version is not None:
            archive.writestr("meta", package_meta(version))
        payload = db_bytes
        if compress:
            from compression import zstd

            payload = zstd.compress(payload)
        archive.writestr(filename, payload)
        if media_entries:
            entries = b"".join(
                b"\x0a" + _varint(len(entry)) + entry
                for entry in (b"\x0a\x05a.png" for _ in range(media_entries))
            )
            archive.writestr("media", entries)
    return buffer.getvalue()


def build_v18_collection(
    notes: list[tuple[str, ...]],
    *,
    fields: tuple[str, ...] = ("Front", "Back"),
    notetype_name: str = "Basic",
    deck_name: str = "Test deck",
    extra_notetypes: list[tuple[str, tuple[str, ...], list[tuple[str, ...]]]] | None = None,
) -> bytes:
    """Create a minimal schema-18 collection that mirrors Anki's layout.

    ``extra_notetypes`` is a list of ``(name, fields, notes)`` tuples for
    multi-notetype packages.
    """
    statements = [
        "CREATE TABLE col (id integer PRIMARY KEY, ver integer NOT NULL)",
        "CREATE TABLE notes (id integer PRIMARY KEY, guid text, mid integer, flds text, tags text)",
        "CREATE TABLE cards (id integer PRIMARY KEY, nid integer, did integer)",
        "CREATE TABLE notetypes (id integer PRIMARY KEY, name text COLLATE unicase, mtime_secs integer, usn integer, config blob)",
        "CREATE TABLE fields (ntid integer, ord integer, name text COLLATE unicase, config blob, PRIMARY KEY (ntid, ord))",
        "CREATE TABLE decks (id integer PRIMARY KEY, name text COLLATE unicase, mtime_secs integer, usn integer, common blob, kind blob)",
        "INSERT INTO col (id, ver) VALUES (1, 18)",
    ]

    notetype_id = 1000
    deck_id = 2000
    statements.append(f"INSERT INTO decks VALUES ({deck_id}, '{deck_name}', 0, 0, x'', x'')")

    all_types = [(notetype_name, fields, notes)]
    if extra_notetypes:
        all_types.extend(extra_notetypes)

    note_id = 1
    for offset, (name, type_fields, type_notes) in enumerate(all_types):
        type_id = notetype_id + offset
        statements.append(
            f"INSERT INTO notetypes VALUES ({type_id}, '{name}', 0, 0, x'')"
        )
        for ordinal, field_name in enumerate(type_fields):
            statements.append(
                f"INSERT INTO fields VALUES ({type_id}, {ordinal}, '{field_name}', x'')"
            )
        for values in type_notes:
            joined = "\x1f".join(values)
            statements.append(
                "INSERT INTO notes VALUES "
                f"({note_id}, 'guid{note_id}', {type_id}, '{joined}', '')"
            )
            statements.append(
                f"INSERT INTO cards VALUES ({note_id + 9000}, {note_id}, {deck_id})"
            )
            note_id += 1

    return build_sqlite(statements)


def build_v11_collection(notes: list[tuple[str, str, str]]) -> bytes:
    """Legacy schema 11 keeps notetypes and decks as JSON inside ``col``."""
    models = {
        "1000": {
            "id": 1000,
            "name": "Legacy",
            "flds": [
                {"name": "Front", "ord": 0},
                {"name": "Back", "ord": 1},
            ],
        }
    }
    decks = {"1": {"id": 1, "name": "Legacy deck"}}
    statements = [
        "CREATE TABLE col (id integer PRIMARY KEY, ver integer NOT NULL, models text, decks text)",
        "CREATE TABLE notes (id integer PRIMARY KEY, guid text, mid integer, flds text, tags text)",
        "CREATE TABLE cards (id integer PRIMARY KEY, nid integer, did integer)",
        "INSERT INTO col VALUES (1, 11, '{}', '{}')".format(
            json.dumps(models).replace("'", "''"),
            json.dumps(decks).replace("'", "''"),
        ),
    ]
    for index, (front, back, _meaning) in enumerate(notes, start=1):
        statements.append(
            "INSERT INTO notes VALUES "
            f"({index}, 'g{index}', 1000, '{front}\x1f{back}', '')"
        )
        statements.append(f"INSERT INTO cards VALUES ({index}, {index}, 1)")
    return build_sqlite(statements)
