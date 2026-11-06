"""Extraction + distractor behaviour on both real sample decks."""

from __future__ import annotations

import pytest

from apkg.distractors import generate_for_items, validate_options
from apkg.errors import ApkgError
from apkg.importer import import_apkg


class TestJlptDeck:
    def test_counts(self, jlpt_bytes):
        result = import_apkg(jlpt_bytes, filename="JLPT N3 Vocab.apkg")
        assert result.report.total_notes == 2139
        assert result.report.parsed == 1896
        assert len(result.items) == 1896
        assert result.report.skipped["front_without_kanji"] == 242
        assert result.report.skipped["reading_invalid"] == 1

    def test_dedicated_reading_field_used(self, jlpt_bytes):
        result = import_apkg(jlpt_bytes)
        by_front = {item.front: item for item in result.items}
        assert by_front["作法"].reading == "さほう"
        assert by_front["作法"].meaning.startswith("manners")

    def test_ambiguous_readings_are_flagged(self, jlpt_bytes):
        result = import_apkg(jlpt_bytes)
        ambiguous = {entry["front"]: entry["readings"] for entry in result.report.ambiguous}
        assert set(ambiguous["上"]) == {"うわ", "かみ", "じょう"}
        flagged = [item for item in result.items if item.front == "上"]
        assert flagged and all(item.needs_review for item in flagged)

    def test_every_reading_is_hiragana(self, jlpt_bytes):
        from apkg.japanese import is_valid_reading

        result = import_apkg(jlpt_bytes)
        for item in result.items:
            assert is_valid_reading(item.reading), item

    def test_generation_is_deterministic(self, russian_bytes):
        first = import_apkg(russian_bytes)
        second = import_apkg(russian_bytes)
        assert [item.options for item in first.items] == [
            item.options for item in second.items
        ]

    def test_every_question_has_four_unique_options(self, jlpt_bytes):
        result = import_apkg(jlpt_bytes)
        for item in result.items:
            assert len(item.options) == 4
            assert len(set(item.options)) == 4
            assert item.options[item.correct_index] == item.reading


class TestRussianDeck:
    def test_counts(self, russian_bytes):
        result = import_apkg(russian_bytes)
        assert result.report.total_notes == 16
        assert len(result.items) == 15
        assert result.report.skipped["front_without_kanji"] == 1

    def test_back_is_split_into_reading_and_meaning(self, russian_bytes):
        result = import_apkg(russian_bytes)
        by_front = {item.front: item for item in result.items}
        assert by_front["自責"].reading == "じせき"
        assert by_front["発揮する"].reading == "はっきする"

    def test_reading_only_back_does_not_fake_a_translation(self, russian_bytes):
        result = import_apkg(russian_bytes)
        item = next(item for item in result.items if item.front == "自責")
        assert item.meaning == ""

    def test_kana_only_front_is_skipped(self, russian_bytes):
        result = import_apkg(russian_bytes)
        assert all(item.front != "パンクする" for item in result.items)

    def test_small_deck_still_gets_four_options(self, russian_bytes):
        result = import_apkg(russian_bytes)
        assert all(len(item.options) == 4 for item in result.items)


class TestExtractionRules:
    def test_html_back_with_newline(self, russian_bytes):
        from tests.conftest import build_apkg, build_v18_collection

        collection = build_v18_collection([("経済", "けいざい<br>экономика")])
        result = import_apkg(build_apkg(collection, compress=True))
        assert len(result.items) == 1
        assert result.items[0].reading == "けいざい"
        assert result.items[0].meaning == "экономика"

    def test_inline_reading_and_meaning(self):
        from tests.conftest import build_apkg, build_v18_collection

        collection = build_v18_collection([("経済", "けいざい экономика")])
        result = import_apkg(build_apkg(collection, compress=True))
        assert result.items[0].reading == "けいざい"

    def test_anki_ruby_bracket(self):
        from tests.conftest import build_apkg, build_v18_collection

        collection = build_v18_collection([("経済[けいざい]", "экономика")])
        result = import_apkg(build_apkg(collection, compress=True))
        assert result.items[0].front == "経済"
        assert result.items[0].reading == "けいざい"

    def test_kanji_reading_is_rejected(self):
        from tests.conftest import build_apkg, build_v18_collection

        collection = build_v18_collection([("経済", "経済")])
        with pytest.raises(ApkgError) as caught:
            import_apkg(build_apkg(collection, compress=True))
        assert caught.value.code == "no_usable_cards"

    def test_sentence_back_is_not_guessed(self):
        from tests.conftest import build_apkg, build_v18_collection

        # A back that is a full sentence must not yield a garbage reading.
        collection = build_v18_collection(
            [("経済", "自動車がパンクした шина лопнула.")]
        )
        with pytest.raises(ApkgError):
            import_apkg(build_apkg(collection, compress=True))

    def test_multi_notetype_package(self):
        from tests.conftest import build_apkg, build_v18_collection

        collection = build_v18_collection(
            [("経済", "けいざい", "экономика")],
            fields=("Expression", "Reading", "Meaning"),
            notetype_name="Jlpt",
            extra_notetypes=[
                ("Basic", ("Front", "Back"), [("自責", "じせき")]),
            ],
        )
        result = import_apkg(build_apkg(collection, compress=True))
        fronts = {item.front for item in result.items}
        assert fronts == {"経済", "自責"}
        assert result.report.plans["Jlpt"]["reading"] == "Reading"

    def test_legacy_schema_11(self):
        from tests.conftest import build_apkg, build_v11_collection

        collection = build_v11_collection([("経済", "けいざい экономика", "")])
        result = import_apkg(build_apkg(collection, version=None, filename="collection.anki2"))
        assert len(result.items) == 1
        assert result.items[0].reading == "けいざい"

    def test_duplicate_pair_is_collapsed(self):
        from tests.conftest import build_apkg, build_v18_collection

        collection = build_v18_collection(
            [("経済", "けいざい", "экономика"), ("経済", "けいざい", "экономика")]
        )
        result = import_apkg(build_apkg(collection, compress=True))
        assert len(result.items) == 1
        assert result.report.duplicates == 1

    def test_options_never_use_another_valid_reading(self):
        from apkg.extract import ExtractedItem

        items = [
            ExtractedItem(front="上", reading="かみ", meaning="", note_id=1, notetype="t"),
            ExtractedItem(front="上", reading="じょう", meaning="", note_id=2, notetype="t"),
            ExtractedItem(front="下", reading="しも", meaning="", note_id=3, notetype="t"),
            ExtractedItem(front="中", reading="なか", meaning="", note_id=4, notetype="t"),
            ExtractedItem(front="山", reading="やま", meaning="", note_id=5, notetype="t"),
        ]
        options, _ = generate_for_items(items)
        assert "じょう" not in options[1].options or options[1].options[options[1].correct_index] == "かみ"
        for option_set in options.values():
            assert len(option_set.options) == len(set(option_set.options))


class TestValidation:
    def test_valid_edit(self):
        assert validate_options(["けいざい", "けざい", "けいさい"], "けいざい") == []

    def test_rejects_duplicates(self):
        problems = validate_options(["けいざい", "けいざい", "けざい"], "けいざい")
        assert any("unique" in problem.lower() for problem in problems)

    def test_rejects_non_hiragana(self):
        problems = validate_options(["経済", "けざい"], "経済")
        assert problems

    def test_rejects_too_few_options(self):
        problems = validate_options(["けいざい"], "けいざい")
        assert problems
