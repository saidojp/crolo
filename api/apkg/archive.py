"""Open an Anki ``.apkg`` archive and hand back the collection database.

Modern packages (Anki 2.1.50+) contain:

    meta                 protobuf PackageMetadata
    collection.anki21b   zstd-compressed SQLite database (schema 18)
    media                protobuf MediaEntries (also zstd)

Legacy packages contain a plain ``collection.anki2`` or
``collection.anki21``. A modern package *also* ships a stub
``collection.anki2`` whose only note tells the user to upgrade Anki, so the
``meta`` version must decide which file to read.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from apkg import proto
from apkg.errors import ApkgError

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

DEFAULT_MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_COLLECTION_BYTES = 500 * 1024 * 1024

META_VERSION_LEGACY1 = 1
META_VERSION_LEGACY2 = 2
META_VERSION_LATEST = 3

COLLECTION_FILES = (
    "collection.anki21b",
    "collection.anki21",
    "collection.anki2",
)


@dataclass(frozen=True)
class CollectionArchive:
    """A decoded collection database plus provenance for the import report."""

    data: bytes
    filename: str
    version: int
    is_legacy: bool
    media_count: int


def _decompress_zstd(data: bytes, *, max_bytes: int) -> bytes:
    """Decompress with a hard output cap (guards against zip bombs)."""
    try:
        from compression import zstd  # Python 3.14+
    except ImportError:  # pragma: no cover - exercised on Python < 3.14
        zstd = None

    if zstd is not None:
        frame = zstd.get_frame_info(data)
        if frame.decompressed_size and frame.decompressed_size > max_bytes:
            raise ApkgError(
                "collection_too_large",
                "The collection expands beyond the allowed size",
            )
        try:
            return zstd.decompress(data, max_output_size=max_bytes)
        except TypeError:
            # Older signature without the safety cap.
            out = zstd.decompress(data)
            if len(out) > max_bytes:
                raise ApkgError(
                    "collection_too_large",
                    "The collection expands beyond the allowed size",
                )
            return out
        except Exception as exc:  # zstd.ZstdError and friends
            raise ApkgError("corrupt_archive", f"Could not decompress the collection: {exc}")

    try:
        import zstandard  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        raise ApkgError(
            "zstd_unavailable",
            "This package uses zstd compression; install the 'zstandard' Python package",
        )

    try:
        reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data))
        out = reader.read(max_bytes + 1)
    except Exception as exc:  # pragma: no cover
        raise ApkgError("corrupt_archive", f"Could not decompress the collection: {exc}")
    if len(out) > max_bytes:
        raise ApkgError("collection_too_large", "The collection expands beyond the allowed size")
    return out


def _choose_collection(
    archive: zipfile.ZipFile,
    version: int,
) -> tuple[str, bool]:
    """Pick the collection filename and whether it is zstd-compressed."""
    if version == META_VERSION_LATEST:
        if "collection.anki21b" not in archive.namelist():
            raise ApkgError(
                "corrupt_archive",
                "The package declares the modern format but has no collection.anki21b",
            )
        return "collection.anki21b", True

    if version == META_VERSION_LEGACY2:
        if "collection.anki21" in archive.namelist():
            return "collection.anki21", False
        if "collection.anki2" in archive.namelist():
            return "collection.anki2", False

    if version in (0, META_VERSION_LEGACY1):
        if "collection.anki21" in archive.namelist():
            return "collection.anki21", False
        if "collection.anki2" in archive.namelist():
            return "collection.anki2", False
        raise ApkgError("corrupt_archive", "No Anki collection database found in the package")

    raise ApkgError(
        "unsupported_version",
        f"The package uses an unsupported format version ({version})",
    )


def open_apkg(
    raw: bytes,
    *,
    max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
    max_collection_bytes: int = DEFAULT_MAX_COLLECTION_BYTES,
) -> CollectionArchive:
    """Validate an ``.apkg`` payload and return its decoded collection."""
    if not raw:
        raise ApkgError("empty_file", "The uploaded file is empty")
    if len(raw) > max_archive_bytes:
        raise ApkgError("file_too_large", "The uploaded file is too large")

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise ApkgError("not_a_zip", "The file is not a valid .apkg archive")

    with archive:
        names = set(archive.namelist())
        if not any(name in names for name in COLLECTION_FILES):
            raise ApkgError("corrupt_archive", "The archive does not contain an Anki collection")

        version = 0
        if "meta" in names:
            try:
                version = proto.package_version(archive.read("meta"))
            except ValueError as exc:
                raise ApkgError("corrupt_archive", f"Invalid package metadata: {exc}")
            if version == 0:
                raise ApkgError(
                    "unsupported_version",
                    "The package was created by an unsupported, newer version of Anki",
                )

        filename, compressed = _choose_collection(archive, version)
        try:
            payload = archive.read(filename)
        except (KeyError, RuntimeError) as exc:
            raise ApkgError("corrupt_archive", f"Could not read {filename}: {exc}")

        # Trust the bytes over the metadata when they clearly disagree.
        if payload.startswith(ZSTD_MAGIC) and not compressed:
            compressed = True
        elif compressed and not payload.startswith(ZSTD_MAGIC):
            compressed = False

        if compressed:
            data = _decompress_zstd(payload, max_bytes=max_collection_bytes)
        else:
            if len(payload) > max_collection_bytes:
                raise ApkgError(
                    "collection_too_large",
                    "The collection exceeds the allowed size",
                )
            data = payload

        if not data.startswith(b"SQLite format 3"):
            raise ApkgError("corrupt_archive", "The collection database is not valid SQLite")

        media_count = 0
        if "media" in names:
            try:
                media = archive.read("media")
                if media.startswith(ZSTD_MAGIC):
                    media = _decompress_zstd(media, max_bytes=16 * 1024 * 1024)
                media_count = proto.count_media_entries(media)
            except (ApkgError, ValueError):
                media_count = 0

    return CollectionArchive(
        data=data,
        filename=filename,
        version=version,
        is_legacy=version in (META_VERSION_LEGACY1, META_VERSION_LEGACY2),
        media_count=media_count,
    )
