"""Convert Anki field HTML into plain text.

Anki fields routinely contain ``<br>``, ``<div>``, ``<b>``, ``[sound:...]`` and
either ``<ruby>`` markup or the ``漢字[かんじ]`` convention. Rather than regexing
HTML, we walk it with the stdlib parser and keep line structure.

The extractor also wants ruby annotations separately, so :func:`parse_field`
returns both the visible text and any readings found in ``<rt>`` or brackets.
"""

from __future__ import annotations

import html as html_module
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

BLOCK_TAGS = {
    "br", "div", "p", "li", "tr", "td", "th", "ul", "ol", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "blockquote",
    "hr", "dt", "dd", "pre",
}
SKIP_TAGS = {"script", "style", "head", "title"}
SOUND_RE = re.compile(r"\[sound:[^\]]*\]")
BRACKET_READING_RE = re.compile(r"\[([\u3041-\u3096\u309d-\u309f\u30fc]+)\]")
CLOZE_RE = re.compile(r"\{\{c\d+::(.*?)(?:::[^}]*)?\}\}", re.DOTALL)


@dataclass
class ParsedField:
    """Plain text plus ruby readings discovered while parsing."""

    text: str
    ruby_readings: list[str] = field(default_factory=list)
    bracket_readings: list[str] = field(default_factory=list)
    had_html: bool = False

    @property
    def readings(self) -> list[str]:
        return [*self.ruby_readings, *self.bracket_readings]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ruby_readings: list[str] = []
        self.had_html = False
        self._skip_depth = 0
        self._rt_depth = 0
        self._rt_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        self.had_html = True
        if lowered in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if lowered == "rt":
            self._rt_depth += 1
            self._rt_buffer = []
            return
        if lowered == "rp":
            self._rt_depth += 1
            return
        if lowered in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag.lower() in BLOCK_TAGS:
            self.had_html = True
            if not self._skip_depth:
                self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if lowered in ("rt", "rp"):
            self._rt_depth = max(0, self._rt_depth - 1)
            if lowered == "rt":
                reading = "".join(self._rt_buffer).strip()
                if reading:
                    self.ruby_readings.append(reading)
                self._rt_buffer = []
            return
        if lowered in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._rt_depth:
            self._rt_buffer.append(data)
            return
        self.parts.append(data)


def _clean_lines(text: str) -> str:
    text = text.replace("\u00a0", " ")
    lines: list[str] = []
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def parse_field(raw: str) -> ParsedField:
    """Parse one Anki field into text and the readings it embeds."""
    if not raw:
        return ParsedField(text="")

    value = CLOZE_RE.sub(r"\1", raw)

    had_html = bool(re.search(r"<[a-zA-Z/!][^>]*>", value))
    if had_html:
        parser = _TextExtractor()
        try:
            parser.feed(value)
            parser.close()
        except Exception:
            # Malformed markup: fall back to stripping tags.
            parser.parts = [re.sub(r"<[^>]+>", " ", value)]
        text = "".join(parser.parts)
        ruby_readings = parser.ruby_readings
        had_html = parser.had_html
    else:
        text = value
        ruby_readings = []

    bracket_readings = [m.group(1) for m in BRACKET_READING_RE.finditer(text)]
    text = SOUND_RE.sub(" ", text)
    text = BRACKET_READING_RE.sub("", text)
    text = html_module.unescape(text)
    text = _clean_lines(text)

    return ParsedField(
        text=text,
        ruby_readings=ruby_readings,
        bracket_readings=bracket_readings,
        had_html=had_html,
    )


def plain_text(raw: str) -> str:
    return parse_field(raw).text
