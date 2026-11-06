"""Tiny protobuf reader.

Anki's ``meta`` file is a two-byte ``PackageMetadata`` message (field 1 is a
varint version), and the modern ``media`` file is a repeated ``MediaEntries``
message. Pulling in a protobuf runtime for that would be overkill, so we read
just the wire format we need.
"""

from __future__ import annotations

from typing import Iterator

WIRE_VARINT = 0
WIRE_64BIT = 1
WIRE_LENGTH = 2
WIRE_32BIT = 5


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValueError("truncated varint")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, offset
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")


def iter_fields(data: bytes) -> Iterator[tuple[int, int, object]]:
    """Yield ``(field_number, wire_type, value)`` triples."""
    offset = 0
    while offset < len(data):
        key, offset = _read_varint(data, offset)
        field_number = key >> 3
        wire_type = key & 0x07
        if field_number == 0:
            raise ValueError("invalid field number")
        if wire_type == WIRE_VARINT:
            value, offset = _read_varint(data, offset)
        elif wire_type == WIRE_64BIT:
            value = data[offset : offset + 8]
            offset += 8
        elif wire_type == WIRE_LENGTH:
            length, offset = _read_varint(data, offset)
            value = data[offset : offset + length]
            offset += length
        elif wire_type == WIRE_32BIT:
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"unsupported wire type {wire_type}")
        if offset > len(data):
            raise ValueError("truncated message")
        yield field_number, wire_type, value


def package_version(meta: bytes) -> int:
    """Return ``PackageMetadata.version`` (0 when unset)."""
    for field_number, wire_type, value in iter_fields(meta):
        if field_number == 1 and wire_type == WIRE_VARINT:
            return int(value)  # type: ignore[arg-type]
    return 0


def count_media_entries(media: bytes) -> int:
    """Count repeated ``MediaEntries.entries`` messages."""
    count = 0
    for field_number, wire_type, _value in iter_fields(media):
        if field_number == 1 and wire_type == WIRE_LENGTH:
            count += 1
    return count
