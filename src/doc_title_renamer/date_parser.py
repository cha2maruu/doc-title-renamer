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
_JAPANESE_ERA_RE = re.compile(r"(明治|大正|昭和|平成|令和)(元|\d+)年")


def normalize_japanese_era(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        era, era_year_text = match.groups()
        era_year = 1 if era_year_text == "元" else int(era_year_text)
        if era_year < 1:
            return match.group(0)
        western_year = _ERA_START_YEARS[era] + era_year - 1
        return f"{western_year}年"

    return _JAPANESE_ERA_RE.sub(replace, text)


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
