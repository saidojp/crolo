"""Japanese text helpers: normalisation, validation and mora edits.

The quiz only ever asks about readings, so the rules here are deliberately
narrow: a reading must be hiragana (plus the long-vowel mark) and a prompt must
contain at least one kanji.
"""

from __future__ import annotations

import re
import unicodedata

KANJI_RANGES = (
    "\u3400-\u4dbf"  # CJK Extension A
    "\u4e00-\u9fff"  # CJK Unified Ideographs
    "\uf900-\ufaff"  # CJK Compatibility Ideographs
)
KANJI_RE = re.compile(f"[{KANJI_RANGES}]")

HIRAGANA_RANGES = "\u3041-\u3096\u309d-\u309f"
HIRAGANA_RE = re.compile(f"[{HIRAGANA_RANGES}]")
# A valid reading: hiragana + the prolonged sound mark.
READING_RE = re.compile(f"^[{HIRAGANA_RANGES}\u30fc]+$")

KATAKANA_START = 0x30A1
KATAKANA_END = 0x30F6
KATAKANA_TO_HIRAGANA_OFFSET = 0x60

LATIN_OR_CYRILLIC_RE = re.compile(r"[A-Za-z\u0400-\u04ff]")
SEPARATOR_RE = re.compile(r"[\s\u3000:：\-–—・/／|]+")
TRAILING_QUALIFIER_RE = re.compile(r"\s*[\(（][^)）]*[\)）]\s*$")

# Voiced/unvoiced/handakuten pairs used by strategy A.
VOICED = {
    "か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
    "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
    "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
    "は": "ば", "ひ": "び", "ふ": "ぶ", "へ": "べ", "ほ": "ぼ",
}
UNVOICED = {voiced: plain for plain, voiced in VOICED.items()}
HANDakuten = {"は": "ぱ", "ひ": "ぴ", "ふ": "ぷ", "へ": "ぺ", "ほ": "ぽ"}
UNHANDakuten = {hand: plain for plain, hand in HANDakuten.items()}

SMALL_TO_LARGE = {
    "っ": "つ", "ゃ": "や", "ゅ": "ゆ", "ょ": "よ",
}
# Contracted sounds are only plausible when the small kana follows an i-row
# mora; turning a standalone や into ゃ (さゆう -> さゅう) is nonsense.
YOON_STEMS = set("きしちにひみりぎじびぴ")
LARGE_TO_SMALL = {"や": "ゃ", "ゆ": "ゅ", "よ": "ょ"}
# Plausible yo-on contractions that are often mis-heard as two morae.
YOON = {"きゃ": "きや", "きゅ": "きゆ", "きょ": "きよ", "しゃ": "しや",
         "しゅ": "しゆ", "しょ": "しよ", "ちゃ": "ちや", "ちゅ": "ちゆ",
         "ちょ": "ちよ", "にゃ": "にや", "にゅ": "にゆ", "にょ": "によ",
         "ひゃ": "ひや", "ひゅ": "ひゆ", "ひょ": "ひよ", "みゃ": "みや",
         "みゅ": "みゆ", "みょ": "みよ", "りゃ": "りや", "りゅ": "りゆ",
         "りょ": "りよ", "ぎゃ": "ぎや", "ぎゅ": "ぎゆ", "ぎょ": "ぎよ",
         "じゃ": "じや", "じゅ": "じゆ", "じょ": "じよ", "びゃ": "びや",
         "びゅ": "びゆ", "びょ": "びよ", "ぴゃ": "ぴや", "ぴゅ": "ぴゆ",
         "ぴょ": "ぴよ"}
YOON_REVERSE = {plain: contracted for contracted, plain in YOON.items()}

SOKUON_FOLLOWERS = set("かきくけこさしすせそたちつてとはひふへほぱぴぷぺぽ")
LONG_VOWEL_ENDINGS = {
    "お": ("う",), "こ": ("う",), "そ": ("う",), "と": ("う",), "の": ("う",),
    "ほ": ("う",), "も": ("う",), "よ": ("う",), "ろ": ("う",), "ご": ("う",),
    "ぞ": ("う",), "ど": ("う",), "ぼ": ("う",), "ぽ": ("う",),
    "え": ("い",), "け": ("い",), "せ": ("い",), "て": ("い",), "ね": ("い",),
    "へ": ("い",), "め": ("い",), "れ": ("い",), "げ": ("い",), "ぜ": ("い",),
    "で": ("い",), "べ": ("い",), "ぺ": ("い",),
}


def kata_to_hira(text: str) -> str:
    """Convert katakana to hiragana, leaving every other character alone."""
    result: list[str] = []
    for char in text:
        code = ord(char)
        if KATAKANA_START <= code <= KATAKANA_END:
            result.append(chr(code - KATAKANA_TO_HIRAGANA_OFFSET))
        else:
            result.append(char)
    return "".join(result)


def normalize_reading(raw: str) -> str:
    """Turn a raw reading field into a canonical hiragana string.

    Returns an empty string when the value cannot be a reading.
    """
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", raw).strip()
    text = TRAILING_QUALIFIER_RE.sub("", text)
    text = kata_to_hira(text)
    text = SEPARATOR_RE.sub("", text)
    return text


def is_valid_reading(reading: str) -> bool:
    if not reading or len(reading) > 40:
        return False
    if KANJI_RE.search(reading) or LATIN_OR_CYRILLIC_RE.search(reading):
        return False
    return bool(READING_RE.fullmatch(reading))


def has_kanji(text: str) -> bool:
    return bool(KANJI_RE.search(text))


def has_kana(text: str) -> bool:
    return bool(HIRAGANA_RE.search(text))


def leading_kana(text: str) -> tuple[str, str]:
    """Split ``けいざい экономика`` into ``("けいざい", "экономика")``.

    Returns ``("", text)`` when the string does not start with kana.
    """
    match = re.match(f"^([{HIRAGANA_RANGES}\u30fc]+)(?:[\\s\u3000:：\\-–—]+(.*))?$", text)
    if not match:
        return "", text
    reading = match.group(1)
    rest = match.group(2) or ""
    return reading, rest.strip()


def mora_edits(reading: str) -> set[str]:
    """Generate single-edit mis-readings of ``reading`` (strategy A)."""
    candidates: set[str] = set()

    def add(value: str) -> None:
        if value != reading and is_valid_reading(value):
            candidates.add(value)

    for index, char in enumerate(reading):
        if char in VOICED:
            add(reading[:index] + VOICED[char] + reading[index + 1:])
        if char in UNVOICED:
            add(reading[:index] + UNVOICED[char] + reading[index + 1:])
        if char in HANDakuten:
            add(reading[:index] + HANDakuten[char] + reading[index + 1:])
        if char in UNHANDakuten:
            add(reading[:index] + UNHANDakuten[char] + reading[index + 1:])
        if char == "っ" and index > 0:
            add(reading[:index] + reading[index + 1:])
        if char == "ー":
            add(reading[:index] + reading[index + 1:])
        if char in SMALL_TO_LARGE:
            add(reading[:index] + SMALL_TO_LARGE[char] + reading[index + 1:])
        if (
            char in LARGE_TO_SMALL
            and index > 0
            and reading[index - 1] in YOON_STEMS
        ):
            add(reading[:index] + LARGE_TO_SMALL[char] + reading[index + 1:])
        if char in SOKUON_FOLLOWERS and index > 0 and reading[index - 1] != "っ":
            add(reading[:index] + "っ" + reading[index:])
        # Long vowel written with a kana: さほう -> さほ, ゆうせん -> ゆせん.
        if char in LONG_VOWEL_ENDINGS and index + 1 < len(reading):
            if reading[index + 1] in LONG_VOWEL_ENDINGS[char]:
                add(reading[: index + 1] + reading[index + 2:])

    for contracted, plain in YOON.items():
        if contracted in reading:
            add(reading.replace(contracted, plain, 1))
    for plain, contracted in YOON_REVERSE.items():
        if plain in reading:
            add(reading.replace(plain, contracted, 1))

    return candidates


def double_edits(reading: str, *, limit: int = 40) -> set[str]:
    """Second-order candidates, used only when single edits are scarce."""
    first = mora_edits(reading)
    result: set[str] = set()
    for candidate in sorted(first):
        for second in mora_edits(candidate):
            if second != reading and second not in first:
                result.add(second)
                if len(result) >= limit:
                    return result
    return result
