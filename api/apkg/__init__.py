"""Anki .apkg parsing and quiz generation.

Public entry point: :func:`apkg.importer.import_apkg`.
"""

from apkg.importer import ImportResult, import_apkg
from apkg.errors import ApkgError

__all__ = ["ImportResult", "import_apkg", "ApkgError"]
