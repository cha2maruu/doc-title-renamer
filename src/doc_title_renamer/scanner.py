from __future__ import annotations

from pathlib import Path

TARGET_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".pdf"}
OFFICE_TEMP_PREFIX = "~$"


def _is_target_file(path: Path) -> bool:
    return (
        path.is_file()
        and not path.name.startswith(OFFICE_TEMP_PREFIX)
        and path.suffix.lower() in TARGET_EXTENSIONS
    )


def resolve_targets(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        candidates = [path for path in input_path.iterdir() if _is_target_file(path)]
        return sorted(candidates, key=lambda path: path.name)

    if _is_target_file(input_path):
        return [input_path]
    return []


def resolve_organize_base_dir(input_path: Path) -> Path:
    if input_path.is_dir():
        return input_path
    return input_path.parent
