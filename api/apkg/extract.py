"""Turn Anki notes into quiz items: prompt (kanji), reading and translation.

Card layouts differ wildly between decks, so the extractor resolves the role of
each field by name first and by content second. Anything ambiguous is reported
rather than guessed: a wrong "correct" reading is worse than a skipped card.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from apkg import japanese
from apkg.html_text import parse_field
from apkg.schema import Collection, Note, Notetype

FRONT_NAMES = (
    "expression", "front", "word", "vocab", "vocabulary", "kanji", "term",
    "слово", "слово на кандзи",
)
READING_NAMES = (
    "reading", "furigana", "kana", "pronunciation", "yomi",
    "чтение", "фуригана",
)
MEANING_NAMES = (
    "meaning", "translation", "english", "definition", "gloss",
    "перевод", "значение", "back",
)
# "Back" is a combined field in many decks, so it is only a *fallback* meaning.
COMBINED_NAMES = ("back", "reverse", "answer")

TRAILING_LATIN_RE = re.compile(r"\s+[A-Za-z\u0400-\u04ff].*$")
RUSSIAN_OR_LATIN_RE = re.compile(r"[A-Za-z\u0400-\u04ff]")

SKIP_EMPTY_FRONT = "empty_front"
SKIP_NO_KANJI = "front_without_kanji"
SKIP_NO_READING = "reading_not_found"
SKIP_INVALID_READING = "reading_invalid"
SKIP_CLOZE = "cloze_unsupported"


@dataclass
class FieldPlan:
    front: int
    reading: int | None
    meaning: int | None
    combined: int | None
    strategy: str


@dataclass
class ExtractedItem:
    front: str
    reading: str
    meaning: str
    note_id: int
    notetype: str
    needs_review: bool = False


@dataclass
class SkipSample:
    front: str
    reason: str


@dataclass
class ExtractionReport:
    total_notes: int = 0
    parsed: int = 0
    quiz_ready: int = 0
    duplicates: int = 0
    needs_review: int = 0
    missing_meaning: int = 0
    skipped: Counter[str] = field(default_factory=Counter)
    skip_samples: list[SkipSample] = field(default_factory=list)
    ambiguous: list[dict[str, object]] = field(default_factory=list)
    plans: dict[str, dict[str, object]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "total_notes": self.total_notes,
            "parsed": self.parsed,
            "quiz_ready": self.quiz_ready,
            "duplicates": self.duplicates,
            "needs_review": self.needs_review,
            "missing_meaning": self.missing_meaning,
            "skipped": dict(self.skipped),
            "skip_samples": [
                {"front": sample.front, "reason": sample.reason}
                for sample in self.skip_samples
            ],
            "ambiguous": self.ambiguous,
            "plans": self.plans,
        }


@dataclass
class ExtractionResult:
    items: list[ExtractedItem]
    report: ExtractionReport


def _normalize_name(name: str) -> str:
    return name.strip().casefold().replace("_", " ")


def _find_by_names(fields: tuple[str, ...], names: tuple[str, ...]) -> int | None:
    normalized = [_normalize_name(name) for name in fields]
    for wanted in names:
        for index, name in enumerate(normalized):
            if name == wanted:
                return index
    # Loose match: field name contains the wanted token (e.g. "Word (kanji)").
    for wanted in names:
        for index, name in enumerate(normalized):
            if wanted in name:
                return index
    return None


def _content_score(fields: tuple[str, ...]) -> list[tuple[float, int]]:
    """Rank fields by how much they look like a kanji prompt."""
    scores: list[tuple[float, int]] = []
    for index, raw in enumerate(fields):
        text = parse_field(raw).text
        if not text:
            continue
        kanji = len(japanese.KANJI_RE.findall(text))
        kana = len(japanese.HIRAGANA_RE.findall(text))
        if kanji == 0:
            continue
        score = kanji / max(1, kanji + kana)
        scores.append((score, index))
    scores.sort(reverse=True)
    return scores


def resolve_plan(notetype: Notetype) -> FieldPlan | None:
    fields = notetype.fields
    if not fields:
        return None

    front = _find_by_names(fields, FRONT_NAMES)
    reading = _find_by_names(fields, READING_NAMES)
    meaning = _find_by_names(fields, MEANING_NAMES)
    combined = _find_by_names(fields, COMBINED_NAMES)

    strategy = "names"
    if front is None:
        ranked = _content_score(fields)
        if not ranked:
            return None
        front = ranked[0][1]
        strategy = "content"
    if reading == front:
        reading = None
    if meaning == front or meaning == reading:
        meaning = None
    if combined == front:
        combined = None
    # "Back" is a poor place to look for a translation when a dedicated field
    # exists, so only use it as a combined fallback.
    if combined is not None and meaning == combined:
        meaning = None
    if combined is None and reading is None:
        # A two-field notetype (Front/Back) almost always keeps the reading on
        # the back; treat the first non-front field as the combined field.
        for index in range(len(fields)):
            if index != front and index != meaning:
                combined = index
                break
    return FieldPlan(front=front, reading=reading, meaning=meaning, combined=combined, strategy=strategy)


def _clean_front(text: str) -> str:
    first_line = text.split("\n", 1)[0].strip()
    first_line = TRAILING_LATIN_RE.sub("", first_line)
    return first_line.strip(" 　:：-–—")


def _meaning_from_field(raw: str) -> str:
    text = parse_field(raw).text
    return " ".join(line.strip() for line in text.split("\n") if line.strip())


def _read_from_combined(raw: str) -> tuple[str, str]:
    """Split ``けいざい экономика`` / ``けいざい<br>экономика``.

    Returns ``(reading, meaning)``. Both may be empty.
    """
    parsed = parse_field(raw)
    if parsed.readings:
        reading = japanese.normalize_reading(parsed.readings[0])
        if reading and japanese.is_valid_reading(reading):
            meaning = parsed.text.replace(parsed.readings[0], "", 1).strip()
            return reading, " ".join(meaning.split())

    lines = [line.strip() for line in parsed.text.split("\n") if line.strip()]
    if not lines:
        return "", parsed.text

    reading, rest = japanese.leading_kana(lines[0])
    if reading:
        meaning_parts = [rest] if rest else []
        meaning_parts.extend(lines[1:])
        return japanese.normalize_reading(reading), " ".join(meaning_parts).strip()

    return "", " ".join(lines).strip()


def _extract_note(
    note: Note,
    notetype: Notetype,
    plan: FieldPlan,
) -> tuple[ExtractedItem | None, str | None]:
    fields = note.fields
    if plan.front >= len(fields):
        return None, SKIP_EMPTY_FRONT

    raw_front = fields[plan.front]
    if "{{c" in raw_front:
        return None, SKIP_CLOZE

    front_parsed = parse_field(raw_front)
    front = _clean_front(front_parsed.text)
    if not front:
        return None, SKIP_EMPTY_FRONT
    if not japanese.has_kanji(front):
        return None, SKIP_NO_KANJI

    reading = ""
    meaning = ""

    if plan.reading is not None and plan.reading < len(fields):
        reading = japanese.normalize_reading(parse_field(fields[plan.reading]).text)
    if not reading and front_parsed.readings:
        reading = japanese.normalize_reading(front_parsed.readings[0])

    combined_rest = ""
    if plan.combined is not None and plan.combined < len(fields):
        combined_reading, combined_rest = _read_from_combined(fields[plan.combined])
        if not reading:
            reading = combined_reading

    if plan.meaning is not None and plan.meaning < len(fields):
        meaning = _meaning_from_field(fields[plan.meaning])
    if not meaning:
        meaning = combined_rest.strip()
    # A "Back" field that only repeats the reading is not a translation.
    if meaning and (meaning == reading or japanese.normalize_reading(meaning) == reading):
        meaning = ""
    if meaning == front:
        meaning = ""

    if not reading:
        return None, SKIP_NO_READING
    if not japanese.is_valid_reading(reading) or reading == front:
        return None, SKIP_INVALID_READING

    return (
        ExtractedItem(
            front=front,
            reading=reading,
            meaning=meaning,
            note_id=note.id,
            notetype=notetype.name,
        ),
        None,
    )


def extract_items(collection: Collection) -> ExtractionResult:
    report = ExtractionReport(total_notes=len(collection.notes))
    plans: dict[int, FieldPlan | None] = {}
    plan_names: dict[str, dict[str, object]] = {}

    for ntid, notetype in collection.notetypes.items():
        plan = resolve_plan(notetype)
        plans[ntid] = plan
        if plan is not None:
            plan_names[notetype.name] = {
                "front": _field_name(notetype, plan.front),
                "reading": _field_name(notetype, plan.reading),
                "meaning": _field_name(notetype, plan.meaning),
                "combined": _field_name(notetype, plan.combined),
                "strategy": plan.strategy,
            }
    report.plans = plan_names

    items_by_pair: dict[tuple[str, str], ExtractedItem] = {}
    skipped_samples: list[SkipSample] = []

    for note in collection.notes:
        notetype = collection.notetype_for(note)
        if notetype is None:
            report.skipped[SKIP_EMPTY_FRONT] += 1
            continue
        plan = plans.get(notetype.id)
        if plan is None:
            report.skipped[SKIP_NO_KANJI] += 1
            continue

        item, reason = _extract_note(note, notetype, plan)
        if item is None:
            assert reason is not None
            report.skipped[reason] += 1
            if len(skipped_samples) < 50:
                skipped_samples.append(
                    SkipSample(front=parse_field(note.fields[plan.front]).text[:40], reason=reason)
                )
            continue

        report.parsed += 1
        key = (item.front, item.reading)
        existing = items_by_pair.get(key)
        if existing is not None:
            report.duplicates += 1
            if not existing.meaning and item.meaning:
                existing.meaning = item.meaning
            continue
        items_by_pair[key] = item

    items = list(items_by_pair.values())

    readings_by_front: dict[str, set[str]] = defaultdict(set)
    for item in items:
        readings_by_front[item.front].add(item.reading)

    ambiguous = {front: readings for front, readings in readings_by_front.items() if len(readings) > 1}
    for item in items:
        if item.front in ambiguous:
            item.needs_review = True
            item.meaning = item.meaning
    for front, readings in sorted(ambiguous.items(), key=lambda pair: pair[0])[:100]:
        report.ambiguous.append(
            {"front": front, "readings": sorted(readings)}
        )

    report.needs_review = sum(1 for item in items if item.needs_review)
    report.missing_meaning = sum(1 for item in items if not item.meaning)
    report.quiz_ready = sum(1 for item in items if not item.needs_review)
    report.skip_samples = skipped_samples
    return ExtractionResult(items=items, report=report)


def _field_name(notetype: Notetype, index: int | None) -> str | None:
    if index is None or index >= len(notetype.fields):
        return None
    return notetype.fields[index]


def summary_deck_name(collection: Collection, filename: str) -> str:
    """Prefer Anki's own deck name, fall back to the uploaded filename."""
    if collection.deck_name:
        return collection.deck_name
    if filename:
        stem = filename.rsplit("/", 1)[-1]
        for suffix in (".apkg", ".colpkg"):
            if stem.casefold().endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        return stem.strip() or "Imported deck"
    return "Imported deck"
