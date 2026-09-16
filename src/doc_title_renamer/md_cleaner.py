from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"[ \t\u3000]+")
_CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\u31f0-\u31ff"
_CJK_SPACE_RE = re.compile(rf"(?<=[{_CJK}]) (?=[{_CJK}])")
_NOISE_LINE_RE = re.compile(r"^(?:[-‐‑‒–—―ー─━_=~.．…・･·•●○]+)$")
_IMAGE_PLACEHOLDER_RE = re.compile(
    r"(?im)^<!--\s*image\s*-->$(?:\n(?:\s*\n)*<!--\s*image\s*-->$)+"
)


def _remove_invisible_characters(text: str) -> str:
    return "".join(
        character
        for character in text
        if character == "\n" or unicodedata.category(character) not in {"Cc", "Cf"}
    )


def clean_markdown(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFKC", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _remove_invisible_characters(text)

    lines: list[str] = []
    for line in text.split("\n"):
        line = _CJK_SPACE_RE.sub("", line.strip())
        if _NOISE_LINE_RE.fullmatch(line) and len(line) >= 3:
            if not lines or lines[-1] != "":
                lines.append("")
            continue
        lines.append(line)

    text = "\n".join(lines)
    text = _IMAGE_PLACEHOLDER_RE.sub("<!-- image -->", text)
    text = re.sub(r"\n(?:[ \t]*\n){3,}", "\n\n", text)
    return text.strip()
