"""High-level ``.apkg`` → quiz-import pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from apkg import distractors
from apkg.archive import CollectionArchive, open_apkg
from apkg.errors import ApkgError
from apkg.extract import ExtractedItem, ExtractionReport, extract_items, summary_deck_name
from apkg.schema import Collection, read_collection
from apkg.sqlite_reader import open_collection


@dataclass
class ImportedItem:
    front: str
    reading: str
    meaning: str
    options: list[str]
    correct_index: int
    source_note_id: int
    notetype: str
    needs_review: bool


@dataclass
class ImportResult:
    deck_name: str
    items: list[ImportedItem]
    report: ExtractionReport
    generator: distractors.GeneratorReport
    archive: CollectionArchive
    collection: Collection
    warnings: list[str] = field(default_factory=list)

    @property
    def quiz_ready(self) -> int:
        return sum(1 for item in self.items if not item.needs_review)

    def summary(self) -> dict[str, object]:
        data = self.report.as_dict()
        data.update(
            {
                "deck_name": self.deck_name,
                "package_version": self.archive.version,
                "collection_file": self.archive.filename,
                "schema_version": self.collection.schema_version,
                "media_count": self.archive.media_count,
                "items": len(self.items),
                "quiz_ready": self.quiz_ready,
                "options": {
                    "four": self.generator.four_options,
                    "three": self.generator.three_options,
                    "two": self.generator.two_options,
                    "strategy_a": self.generator.strategy_a,
                    "strategy_b": self.generator.strategy_b,
                },
                "warnings": [*self.warnings, *self.generator.warnings],
            }
        )
        return data


def import_apkg(raw: bytes, *, filename: str = "") -> ImportResult:
    """Parse an uploaded package end to end.

    Raises :class:`ApkgError` for unreadable packages and when nothing usable
    was found.
    """
    archive = open_apkg(raw)
    with open_collection(archive.data) as con:
        collection = read_collection(con)
        extraction = extract_items(collection)

    if not extraction.items:
        raise ApkgError(
            "no_usable_cards",
            "No cards with a kanji prompt and a hiragana reading were found",
        )

    options_by_note, generator_report = distractors.generate_for_items(extraction.items)

    items: list[ImportedItem] = []
    for item in extraction.items:
        option_set = options_by_note[item.note_id]
        items.append(
            ImportedItem(
                front=item.front,
                reading=item.reading,
                meaning=item.meaning,
                options=option_set.options,
                correct_index=option_set.correct_index,
                source_note_id=item.note_id,
                notetype=item.notetype,
                needs_review=item.needs_review,
            )
        )

    warnings: list[str] = []
    if extraction.report.needs_review:
        warnings.append(
            f"{extraction.report.needs_review} cards have more than one valid reading "
            "and need a decision before they can be quizzed"
        )
    if extraction.report.missing_meaning:
        warnings.append(
            f"{extraction.report.missing_meaning} cards have no translation; "
            "the hint will be empty"
        )

    return ImportResult(
        deck_name=summary_deck_name(collection, filename),
        items=items,
        report=extraction.report,
        generator=generator_report,
        archive=archive,
        collection=collection,
        warnings=warnings,
    )


__all__ = ["ImportResult", "ImportedItem", "import_apkg", "ApkgError", "ExtractedItem"]
