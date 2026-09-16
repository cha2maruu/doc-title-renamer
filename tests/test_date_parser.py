import datetime

from doc_title_renamer.date_parser import (
    is_valid_issue_date,
    normalize_japanese_era,
)


def test_normalize_japanese_era_supports_each_era_and_first_year() -> None:
    text = "明治元年、大正2年、昭和64年、平成元年、令和6年4月1日"

    assert normalize_japanese_era(text) == (
        "1868年、1913年、1989年、1989年、2024年4月1日"
    )


def test_normalize_japanese_era_leaves_other_text_unchanged() -> None:
    assert normalize_japanese_era("発行日は2024年。令和0年は不正。") == (
        "発行日は2024年。令和0年は不正。"
    )


def test_is_valid_issue_date_rejects_invalid_format_and_nonexistent_date() -> None:
    today = datetime.date(2026, 1, 1)

    assert not is_valid_issue_date("2026-2-01", today=today)
    assert not is_valid_issue_date("2026-02-31", today=today)


def test_is_valid_issue_date_accepts_exactly_one_year_ahead() -> None:
    today = datetime.date(2026, 9, 15)

    assert is_valid_issue_date("2027-09-15", today=today)
    assert not is_valid_issue_date("2027-09-16", today=today)


def test_is_valid_issue_date_handles_leap_day_future_threshold() -> None:
    today = datetime.date(2024, 2, 29)

    assert is_valid_issue_date("2025-02-28", today=today)
    assert not is_valid_issue_date("2025-03-01", today=today)
