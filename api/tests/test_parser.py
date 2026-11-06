"""Parser tests pinned to the real sample decks and synthetic packages."""

from __future__ import annotations

import pytest

from apkg.archive import open_apkg
from apkg.errors import ApkgError
from apkg.html_text import parse_field
from apkg.japanese import is_valid_reading, kata_to_hira, mora_edits, normalize_reading
from apkg.schema import read_collection
from apkg.sqlite_reader import open_collection

from tests.conftest import build_apkg


class TestArchive:
    def test_reads_modern_package_from_meta(self, jlpt_bytes):
        archive = open_apkg(jlpt_bytes)
        assert archive.filename == "collection.anki21b"
        assert archive.version == 3
        assert archive.is_legacy is False
        assert archive.data.startswith(b"SQLite format 3")

    def test_ignores_upgrade_stub_in_anki2(self, jlpt_bytes):
        names = zipfile_names(jlpt_bytes)
        assert "collection.anki2" in names
        archive = open_apkg(jlpt_bytes)
        with open_collection(archive.data) as con:
            collection = read_collection(con)
        assert collection.schema_version == 18
        assert len(collection.notes) == 2139

    def test_rejects_non_zip(self):
        with pytest.raises(ApkgError) as caught:
            open_apkg(b"definitely not a zip")
        assert caught.value.code == "not_a_zip"

    def test_rejects_unknown_meta_version(self):
        payload = build_apkg(b"anything", version=9)
        with pytest.raises(ApkgError) as caught:
            open_apkg(payload)
        assert caught.value.code == "unsupported_version"

    def test_rejects_empty_file(self):
        with pytest.raises(ApkgError) as caught:
            open_apkg(b"")
        assert caught.value.code == "empty_file"

    def test_legacy_package_without_meta(self, russian_bytes):
        # Repackage a modern collection as a legacy-style archive.
        archive = open_apkg(russian_bytes)
        payload = build_apkg(
            archive.data, version=None, filename="collection.anki2", compress=False
        )
        legacy = open_apkg(payload)
        assert legacy.filename == "collection.anki2"
        assert legacy.version == 0
        assert legacy.is_legacy is False  # unknown meta means "not modern", still readable


class TestJapanese:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("けいざい", "けいざい"),
            ("ジーンズ", "じーんず"),
            ("すみません (かん)", "すみません"),
            ("けいざい экономика", "けいざいэкономика"),
            ("  ", ""),
        ],
    )
    def test_normalize_reading(self, raw, expected):
        assert normalize_reading(raw) == expected

    def test_kata_to_hira(self):
        assert kata_to_hira("ジュース") == "じゅーす"
        assert kata_to_hira("かな") == "かな"

    @pytest.mark.parametrize("reading", ["けいざい", "じーんず", "はっきする", "あ"])
    def test_valid_readings(self, reading):
        assert is_valid_reading(reading)

    @pytest.mark.parametrize(
        "reading", ["経済", "keizai", "экономика", "けい ざい", "", "けいざい!"]
    )
    def test_invalid_readings(self, reading):
        assert not is_valid_reading(reading)

    def test_mora_edits_cover_common_errors(self):
        edits = mora_edits("けいざい")
        assert "けざい" in edits  # long vowel collapsed
        assert "けいさい" in edits  # devoiced
        assert "けいざい" not in edits

    def test_mora_edits_never_contain_kanji(self):
        for candidate in mora_edits("がっこう"):
            assert is_valid_reading(candidate)

    def test_contraction_only_after_i_row(self):
        assert "さゆう" not in {c for c in mora_edits("さゆう") if "ゅ" in c}


class TestHtml:
    def test_br_becomes_newline(self):
        parsed = parse_field("けいざい<br>экономика")
        assert parsed.text == "けいざい\nэкономика"

    def test_ruby_annotation_kept_separately(self):
        parsed = parse_field("<ruby>経済<rt>けいざい</rt></ruby>")
        assert parsed.text == "経済"
        assert parsed.ruby_readings == ["けいざい"]

    def test_bracket_reading(self):
        parsed = parse_field("経済[けいざい] экономика")
        assert parsed.text == "経済 экономика"
        assert parsed.bracket_readings == ["けいざい"]

    def test_sound_and_images_removed(self):
        parsed = parse_field('経済 [sound:keizai.mp3] <img src="x.png">')
        assert "sound" not in parsed.text
        assert "img" not in parsed.text
        assert parsed.text == "経済"

    def test_script_style_removed(self):
        parsed = parse_field("<style>.x{}</style>けいざい<script>alert(1)</script>")
        assert parsed.text == "けいざい"

    def test_cloze_stripped(self):
        assert parse_field("{{c1::経済::word}}").text == "経済"


def zipfile_names(raw: bytes):
    import zipfile

    with zipfile.ZipFile(__import__("io").BytesIO(raw)) as archive:
        return archive.namelist()
