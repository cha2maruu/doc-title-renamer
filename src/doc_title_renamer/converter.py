from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".pdf"}


@lru_cache(maxsize=1)
def _create_markitdown() -> Any:
    # Keep the MarkItDown import local so lightweight modules/tests can be used
    # without loading the conversion stack until conversion is actually needed.
    from markitdown import MarkItDown

    # enable_plugins=False: never let a third-party plugin package installed in
    # the environment silently change conversion behavior.
    return MarkItDown(enable_plugins=False)


def convert_to_markdown(file_path: Path) -> str:
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"未対応のファイル形式です: {file_path.suffix}")

    md = _create_markitdown()
    result = md.convert_local(file_path)
    return result.markdown
