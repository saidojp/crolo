"""Build the four answer options for a reading question.

Two strategies, mixed per the product spec:

* A — realistic mis-readings of the correct answer (voicing, sokuon, long
  vowels, yo-on, ...).
* B — readings of other words in the same deck.

Everything is deterministic for a given item so that re-generating options in
the editor only changes when asked, and tests stay stable.
"""

from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass, field

from apkg import japanese

OPTION_COUNT = 4
STRATEGY_A_TARGET = 2
SEED = 0xC4010


@dataclass
class OptionSet:
    options: list[str]
    correct_index: int
    strategy_a: int = 0
    strategy_b: int = 0


@dataclass
class GeneratorReport:
    items: int = 0
    four_options: int = 0
    three_options: int = 0
    two_options: int = 0
    generated: int = 0
    strategy_a: int = 0
    strategy_b: int = 0
    warnings: list[str] = field(default_factory=list)


def _seed_for(front: str, reading: str) -> int:
    """Stable seed (``hash()`` is salted per process)."""
    digest = hashlib.sha256(f"{front}\x1f{reading}".encode("utf-8")).digest()
    return SEED ^ int.from_bytes(digest[:4], "big")


def build_pools(items) -> tuple[dict[str, set[str]], list[str]]:
    """Return readings grouped by front plus a de-duplicated reading pool."""
    by_front: dict[str, set[str]] = defaultdict(set)
    seen: list[str] = []
    known: set[str] = set()
    for item in items:
        by_front[item.front].add(item.reading)
        if item.reading not in known:
            known.add(item.reading)
            seen.append(item.reading)
    return by_front, seen


def _similarity(answer: str, candidate: str) -> float:
    """Rough phonetic/visual similarity used to rank pool distractors."""
    if not answer or not candidate:
        return 0.0
    shared = len(set(answer) & set(candidate))
    longest = max(len(answer), len(candidate))
    length_penalty = abs(len(answer) - len(candidate)) / longest
    return shared / longest - length_penalty


def _pool_candidates(answer: str, pool: list[str], blocked: set[str]) -> list[str]:
    """Filter the deck pool down to plausible alternatives.

    Cards in a deck carry unrelated meanings, but a one-mora reading next to a
    four-mora answer is a giveaway. Keep readings within two morae of the
    answer; relax the rule only if nothing is left.
    """
    answer_length = len(answer)
    result: list[str] = []
    fallback: list[str] = []
    for reading in pool:
        if reading in blocked:
            continue
        if len(reading) < 2:
            continue
        if abs(len(reading) - answer_length) <= 2:
            result.append(reading)
        else:
            fallback.append(reading)
    if len(result) < 3:
        result.extend(fallback)
    return result


def generate_options(
    item,
    by_front: dict[str, set[str]],
    pool: list[str],
    *,
    option_count: int = OPTION_COUNT,
    rng: random.Random | None = None,
) -> OptionSet:
    """Pick ``option_count - 1`` distractors and shuffle everything."""
    random_source = rng or random.Random(_seed_for(item.front, item.reading))
    valid_readings = by_front.get(item.front, {item.reading}) | {item.reading}
    pool_candidates = _pool_candidates(item.reading, pool, valid_readings)

    strategy_a: list[str] = []
    for candidate in sorted(japanese.mora_edits(item.reading)):
        if candidate not in valid_readings:
            strategy_a.append(candidate)
    random_source.shuffle(strategy_a)

    chosen: list[str] = []
    chosen_set: set[str] = set()
    for candidate in strategy_a:
        if len(chosen) >= min(STRATEGY_A_TARGET, option_count - 1):
            break
        if candidate not in chosen_set:
            chosen.append(candidate)
            chosen_set.add(candidate)

    a_count = len(chosen)

    # Top up from the deck pool, preferring readings of a similar shape.
    if len(chosen) < option_count - 1:
        need = option_count - 1 - len(chosen)
        available = [reading for reading in pool_candidates if reading not in chosen_set]
        available.sort(key=lambda reading: _similarity(item.reading, reading), reverse=True)
        head = available[: max(need * 4, 12)]
        random_source.shuffle(head)
        for candidate in head[:need]:
            chosen.append(candidate)
            chosen_set.add(candidate)

    # Still short? Allow second-order distortions before shrinking the quiz.
    if len(chosen) < option_count - 1:
        for candidate in sorted(japanese.double_edits(item.reading)):
            if candidate in chosen_set or candidate in valid_readings:
                continue
            chosen.append(candidate)
            chosen_set.add(candidate)
            if len(chosen) >= option_count - 1:
                break

    options = [item.reading, *chosen]
    random_source.shuffle(options)
    return OptionSet(
        options=options,
        correct_index=options.index(item.reading),
        strategy_a=a_count,
        strategy_b=max(0, len(chosen) - a_count),
    )


def generate_for_items(items) -> tuple[dict[int, OptionSet], GeneratorReport]:
    """Generate options for every item, keyed by ``item.note_id``."""
    by_front, pool = build_pools(items)
    report = GeneratorReport(items=len(items))
    results: dict[int, OptionSet] = {}
    for item in items:
        option_set = generate_options(item, by_front, pool)
        results[item.note_id] = option_set
        report.generated += 1
        report.strategy_a += option_set.strategy_a
        report.strategy_b += option_set.strategy_b
        if len(option_set.options) >= 4:
            report.four_options += 1
        elif len(option_set.options) == 3:
            report.three_options += 1
        else:
            report.two_options += 1
    if report.three_options or report.two_options:
        report.warnings.append(
            "Some questions have fewer than four options because the deck is small"
        )
    return results, report


def validate_options(
    options: list[str],
    correct: str,
    *,
    valid_readings: set[str] | None = None,
    min_options: int = 2,
    max_options: int = 4,
) -> list[str]:
    """Return human-readable problems with a user-edited option list."""
    problems: list[str] = []
    cleaned = [option.strip() for option in options if option.strip()]

    if len(cleaned) < min_options:
        problems.append(f"At least {min_options} options are required")
    if len(cleaned) > max_options:
        problems.append(f"At most {max_options} options are allowed")
    if len(set(cleaned)) != len(cleaned):
        problems.append("Options must be unique")
    if cleaned.count(correct) != 1:
        problems.append("The correct reading must appear exactly once")
    for option in cleaned:
        if not japanese.is_valid_reading(option):
            problems.append(f"'{option}' is not a valid hiragana reading")
    if valid_readings:
        conflicts = (set(cleaned) - {correct}) & valid_readings
        if conflicts:
            problems.append(
                "These options are also valid readings: " + ", ".join(sorted(conflicts))
            )
    return problems
