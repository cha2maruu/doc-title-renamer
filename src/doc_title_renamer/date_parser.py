from __future__ import annotations

import datetime
import re


_ERA_START_YEARS = {
    "明治": 1868,
    "大正": 1912,
    "昭和": 1926,
    "平成": 1989,
    "令和": 2019,
}
_ALPHA_ERA_CODES = {
    "M": "明治",
    "T": "大正",
    "S": "昭和",
    "H": "平成",
    "R": "令和",
}
_JAPANESE_ERA_RE = re.compile(r"(明治|大正|昭和|平成|令和)(元|\d+)年")
# ローマ字1文字の元号略記（例: R6年、H31年）。前が英数字だと誤検出しやすいため、
# 直前が英数字でないことを要求する。
_ALPHA_ERA_KANJI_RE = re.compile(r"(?<![A-Za-z0-9])([MTSHR])(元|\d+)年")
# 区切り数字形式の元号略記（例: R6.4.1、H31/4/1）。年・月・日を同じ区切り文字で統一する。
_ALPHA_ERA_DELIMITED_RE = re.compile(
    r"(?<![A-Za-z0-9])([MTSHR])(元|\d{1,2})([./])(\d{1,2})\3(\d{1,2})(?!\d)"
)


def _era_year_to_western(era: str, era_year_text: str) -> int | None:
    era_year = 1 if era_year_text == "元" else int(era_year_text)
    if era_year < 1:
        return None
    return _ERA_START_YEARS[era] + era_year - 1


def normalize_japanese_era(text: str) -> str:
    def replace_kanji(match: re.Match[str]) -> str:
        era, era_year_text = match.groups()
        western_year = _era_year_to_western(era, era_year_text)
        if western_year is None:
            return match.group(0)
        return f"{western_year}年"

    def replace_alpha_kanji(match: re.Match[str]) -> str:
        code, era_year_text = match.groups()
        western_year = _era_year_to_western(_ALPHA_ERA_CODES[code], era_year_text)
        if western_year is None:
            return match.group(0)
        return f"{western_year}年"

    def replace_alpha_delimited(match: re.Match[str]) -> str:
        code, era_year_text, sep, month, day = match.groups()
        western_year = _era_year_to_western(_ALPHA_ERA_CODES[code], era_year_text)
        if western_year is None:
            return match.group(0)
        return f"{western_year}{sep}{month}{sep}{day}"

    text = _JAPANESE_ERA_RE.sub(replace_kanji, text)
    text = _ALPHA_ERA_DELIMITED_RE.sub(replace_alpha_delimited, text)
    text = _ALPHA_ERA_KANJI_RE.sub(replace_alpha_kanji, text)
    return text


def is_valid_issue_date(value: str, *, today: datetime.date | None = None) -> bool:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        return False

    try:
        issue_date = datetime.date.fromisoformat(value)
    except ValueError:
        return False

    reference_date = today or datetime.date.today()
    try:
        future_limit = reference_date.replace(year=reference_date.year + 1)
    except ValueError:
        future_limit = reference_date.replace(
            year=reference_date.year + 1, month=2, day=28
        )
    return issue_date <= future_limit
