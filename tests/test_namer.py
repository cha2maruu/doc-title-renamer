import datetime
from pathlib import Path

import pytest

from doc_title_renamer.namer import (
    MAX_WINDOWS_PATH_LENGTH,
    TITLE_MAX_LENGTH,
    PathLengthError,
    build_new_name,
    fit_path_length,
    is_path_length_valid,
    resolve_collisions,
    sanitize_title,
)


def test_sanitize_title_replaces_windows_forbidden_characters() -> None:
    assert sanitize_title('見積\\書/:*?"<>|') == "見積_書________"


def test_sanitize_title_removes_invisible_characters_and_trailing_marks() -> None:
    assert sanitize_title("件\u200b名\n\t\u2028...  ") == "件名"


def test_sanitize_title_may_return_empty_string() -> None:
    assert sanitize_title("...  ") == ""


def test_build_new_name_keeps_exactly_maximum_length_title() -> None:
    title = "あ" * TITLE_MAX_LENGTH

    result = build_new_name(datetime.date(2026, 4, 15), title, ".PDF")

    assert result == f"20260415_{title}.PDF"


def test_build_new_name_truncates_and_resanitizes_title() -> None:
    title = "あ" * (TITLE_MAX_LENGTH - 1) + "." + "続き"

    result = build_new_name(datetime.date(2026, 4, 15), title, ".pdf")

    assert result == f"20260415_{'あ' * (TITLE_MAX_LENGTH - 1)}.pdf"


def test_resolve_collisions_avoids_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.touch()
    destination = tmp_path / "20260415_見積書.pdf"
    destination.touch()

    assert resolve_collisions([(source, destination)]) == [
        (source, tmp_path / "20260415_見積書_2.pdf")
    ]


def test_resolve_collisions_keeps_incrementing_past_existing_sequence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.pdf"
    source.touch()
    destination = tmp_path / "20260415_見積書.pdf"
    destination.touch()
    destination.with_name("20260415_見積書_2.pdf").touch()

    assert resolve_collisions([(source, destination)]) == [
        (source, tmp_path / "20260415_見積書_3.pdf")
    ]


def test_resolve_collisions_numbers_batch_duplicates_in_input_order(
    tmp_path: Path,
) -> None:
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    destination = tmp_path / "20260415_見積書.pdf"

    assert resolve_collisions([(first, destination), (second, destination)]) == [
        (first, destination),
        (second, tmp_path / "20260415_見積書_2.pdf"),
    ]


def test_resolve_collisions_keeps_no_op_without_numbering(tmp_path: Path) -> None:
    source = tmp_path / "20260415_見積書.pdf"
    source.touch()

    assert resolve_collisions([(source, source)]) == [(source, source)]


def test_resolve_collisions_reserves_no_op_for_later_item(tmp_path: Path) -> None:
    source = tmp_path / "20260415_見積書.pdf"
    other = tmp_path / "other.pdf"
    source.touch()

    result = resolve_collisions([(source, source), (other, source)])

    assert result[1] == (other, tmp_path / "20260415_見積書_2.pdf")


def test_fit_path_length_accepts_exact_full_path_boundary(tmp_path: Path) -> None:
    fixed_length = len("20260415_") + len(".pdf")
    title_length = (
        MAX_WINDOWS_PATH_LENGTH
        - len(str(tmp_path.absolute()))
        - 1
        - fixed_length
    )
    if title_length < 1:
        pytest.skip("一時ディレクトリのパスが境界値テストには長すぎます")
    destination = tmp_path / f"20260415_{'a' * title_length}.pdf"

    assert fit_path_length(destination) == destination
    assert is_path_length_valid(destination)


def test_fit_path_length_shortens_title_past_full_path_boundary(
    tmp_path: Path,
) -> None:
    fixed_length = len("20260415_") + len(".pdf")
    title_length = (
        MAX_WINDOWS_PATH_LENGTH
        - len(str(tmp_path.absolute()))
        - 1
        - fixed_length
    )
    if title_length < 1:
        pytest.skip("一時ディレクトリのパスが境界値テストには長すぎます")
    destination = tmp_path / f"20260415_{'a' * (title_length + 1)}.pdf"

    fitted = fit_path_length(destination)

    assert len(str(fitted.absolute())) == MAX_WINDOWS_PATH_LENGTH
    assert fitted.suffix == ".pdf"


def test_fit_path_length_raises_when_no_title_character_can_fit(
    tmp_path: Path, monkeypatch
) -> None:
    destination = tmp_path / "20260415_a.pdf"
    monkeypatch.setattr(
        "doc_title_renamer.namer._absolute_path_length",
        lambda path: MAX_WINDOWS_PATH_LENGTH + len(path.name),
    )

    with pytest.raises(PathLengthError):
        fit_path_length(destination)
