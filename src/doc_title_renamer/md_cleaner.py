from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"[ \t\u3000]+")
_CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\u31f0-\u31ff"
_CJK_SPACE_RE = re.compile(rf"(?<=[{_CJK}]) (?=[{_CJK}])")
_NOISE_LINE_RE = re.compile(r"^(?:[-‐‑‒–—―ー─━_=~.．…・･·•●○]+)$")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]\n]*\]\([^\n)]*\)")
_CONSECUTIVE_IMAGES_RE = re.compile(
    rf"(?m)^(?P<image>{_MARKDOWN_IMAGE_RE.pattern}) *$"
    rf"(?:\n(?: *\n)* *(?:{_MARKDOWN_IMAGE_RE.pattern}) *$)+"
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
    # MarkItDown emits placeholders as Markdown image lines (for example,
    # ``![Picture 1](Picture1.jpg)``). Keep the first image and its potentially
    # useful alt text, but discard immediately repeated image lines so they do
    # not consume the LLM input budget. RapidOCR output is plain text.
    text = _CONSECUTIVE_IMAGES_RE.sub(r"\g<image>", text)
    text = re.sub(r"\n(?:[ \t]*\n){3,}", "\n\n", text)
    return text.strip()
