"""Typed errors raised while reading Anki packages.

Every failure carries a stable ``code`` so the API layer can map it to a
friendly message without inspecting exception text.
"""

from __future__ import annotations


class ApkgError(Exception):
    """A package could not be read or contained no usable cards."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
