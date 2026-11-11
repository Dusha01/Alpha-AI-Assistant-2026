from __future__ import annotations

import re
from html.parser import HTMLParser

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)


def strip_html(value: str) -> str:
    if not value:
        return ""
    if "<" not in value and ">" not in value:
        return normalize_whitespace(value)
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return normalize_whitespace(" ".join(parser.parts))


def normalize_whitespace(value: str) -> str:
    return _WS_RE.sub(" ", value.strip())
