from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenameResult:
    source: Path
    destination: Path
    success: bool
    error: str | None = None
    no_op: bool = False


def apply_plan(plan: list[tuple[Path, Path]]) -> list[RenameResult]:
    results: list[RenameResult] = []
    for source, destination in plan:
        if source == destination:
            results.append(
                RenameResult(source, destination, success=True, no_op=True)
            )
            continue

        try:
            if not source.is_file():
                raise FileNotFoundError(f"移動元ファイルが見つかりません: {source}")
            if destination.exists():
                raise FileExistsError(f"移動先が既に存在します: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
        except OSError as exc:
            results.append(
                RenameResult(source, destination, success=False, error=str(exc))
            )
        else:
            results.append(RenameResult(source, destination, success=True))
    return results
