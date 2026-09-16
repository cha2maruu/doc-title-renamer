from __future__ import annotations

import datetime
import re
import unicodedata
from pathlib import Path

TITLE_MAX_LENGTH = 40
MAX_WINDOWS_FILENAME_LENGTH = 255
# WindowsのMAX_PATH(260)は終端のヌル文字を含むため、実際に使用できるのは259文字まで。
# フェーズ7の実機検証で260文字ちょうどのパスがrename/writeに失敗することを確認済み。
MAX_WINDOWS_PATH_LENGTH = 259
_INVALID_FILENAME_CHARACTERS_RE = re.compile(r'[\\/:*?"<>|]')
_DATED_STEM_RE = re.compile(r"^(\d{8}_)(.*)$")


class PathLengthError(ValueError):
    def __init__(self, path: Path, source: Path | None = None) -> None:
        self.path = path
        self.source = source
        super().__init__(f"Windowsのパス長制限に収まりません: {path}")


def sanitize_title(title: str) -> str:
    sanitized = _INVALID_FILENAME_CHARACTERS_RE.sub("_", title)
    sanitized = "".join(
        character
        for character in sanitized
        if unicodedata.category(character) not in {"Cc", "Cf", "Zl", "Zp"}
    )
    return sanitized.rstrip(". ")


def build_new_name(issue_date: datetime.date, title: str, extension: str) -> str:
    sanitized_title = sanitize_title(title)
    if len(sanitized_title) > TITLE_MAX_LENGTH:
        sanitized_title = sanitize_title(sanitized_title[:TITLE_MAX_LENGTH])
    return f"{issue_date:%Y%m%d}_{sanitized_title}{extension}"


def _absolute_path_length(path: Path) -> int:
    return len(str(path.absolute()))


def is_path_length_valid(path: Path) -> bool:
    return (
        len(path.name) <= MAX_WINDOWS_FILENAME_LENGTH
        and _absolute_path_length(path) <= MAX_WINDOWS_PATH_LENGTH
    )


def _fit_collision_candidate(destination: Path, number: int | None) -> Path:
    match = _DATED_STEM_RE.fullmatch(destination.stem)
    if match is None:
        prefix = ""
        title = destination.stem
    else:
        prefix, title = match.groups()

    sequence = f"_{number}" if number is not None else ""
    fixed_name_length = len(prefix) + len(sequence) + len(destination.suffix)
    absolute_parent_length = len(str(destination.parent.absolute()))
    available_title_length = min(
        MAX_WINDOWS_FILENAME_LENGTH - fixed_name_length,
        MAX_WINDOWS_PATH_LENGTH - absolute_parent_length - 1 - fixed_name_length,
    )
    if available_title_length < 1:
        raise PathLengthError(destination)

    fitted_title = sanitize_title(title[:available_title_length])
    if not fitted_title:
        raise PathLengthError(destination)
    candidate = destination.with_name(
        f"{prefix}{fitted_title}{sequence}{destination.suffix}"
    )
    if not is_path_length_valid(candidate):
        raise PathLengthError(candidate)
    return candidate


def fit_path_length(destination: Path) -> Path:
    return _fit_collision_candidate(destination, None)


def _reservation_key(path: Path) -> str:
    return str(path.absolute()).casefold()


def resolve_collisions(planned: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    resolved: list[tuple[Path, Path]] = []
    reserved: set[str] = set()

    for source, destination in planned:
        if source == destination:
            if not is_path_length_valid(destination):
                raise PathLengthError(destination, source)
            resolved.append((source, destination))
            reserved.add(_reservation_key(destination))
            continue

        number: int | None = None
        while True:
            try:
                candidate = _fit_collision_candidate(destination, number)
            except PathLengthError as exc:
                raise PathLengthError(exc.path, source) from exc
            if not candidate.exists() and _reservation_key(candidate) not in reserved:
                break
            number = 2 if number is None else number + 1

        resolved.append((source, candidate))
        reserved.add(_reservation_key(candidate))

    return resolved
