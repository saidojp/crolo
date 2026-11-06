"""Open a collection database from memory.

``Connection.deserialize()`` arrived in Python 3.11, so older interpreters fall
back to a temporary file. Anki's schema declares ``COLLATE unicase`` on several
columns; without that collation SQLite refuses to prepare *any* statement
against the table, so we register a case-folded implementation.
"""

from __future__ import annotations

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from apkg.errors import ApkgError


def _unicase(left: str, right: str) -> int:
    a = left.casefold()
    b = right.casefold()
    return (a > b) - (a < b)


def _configure(con: sqlite3.Connection) -> sqlite3.Connection:
    con.create_collation("unicase", _unicase)
    con.execute("PRAGMA query_only = ON")
    return con


def _clear_wal_flag(data: bytes) -> bytes:
    """Mark the database as rollback-journal mode.

    Anki ships collections in WAL mode (header bytes 18/19 == 2). A WAL database
    needs its ``-wal`` sidecar to be opened, which does not exist inside the
    archive, so ``deserialize()`` (and a bare temp file) fails with "unable to
    open database file". The package's main database is checkpointed before
    export, so flipping the header to rollback mode is safe for read-only use.
    """
    if len(data) < 20 or data[18] == 1 and data[19] == 1:
        return data
    patched = bytearray(data)
    patched[18] = 1
    patched[19] = 1
    return bytes(patched)


@contextmanager
def open_collection(data: bytes) -> Iterator[sqlite3.Connection]:
    """Yield a read-only connection and make sure it is always closed."""
    temp_path: str | None = None
    con: sqlite3.Connection | None = None
    try:
        data = _clear_wal_flag(data)
        if hasattr(sqlite3.Connection, "deserialize"):
            con = sqlite3.connect(":memory:")
            con.deserialize(data)
        else:  # pragma: no cover - Python < 3.11
            handle = tempfile.NamedTemporaryFile(suffix=".anki", delete=False)
            handle.write(data)
            handle.close()
            temp_path = handle.name
            con = sqlite3.connect(temp_path)
        yield _configure(con)
    except sqlite3.DatabaseError as exc:
        raise ApkgError("corrupt_collection", f"Could not open the collection: {exc}")
    finally:
        if con is not None:
            con.close()
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)
