from pathlib import Path
from types import SimpleNamespace

import pytest

from doc_title_renamer import converter

from helpers import install_fake_markitdown


def test_create_markitdown_disables_plugins(monkeypatch) -> None:
    fake = install_fake_markitdown(monkeypatch)
    converter._create_markitdown.cache_clear()

    try:
        md = converter._create_markitdown()

        assert isinstance(md, fake.MarkItDown)
        assert md.kwargs == {"enable_plugins": False}
    finally:
        converter._create_markitdown.cache_clear()


def test_convert_to_markdown_uses_markitdown_result(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "document.DOCX"
    calls: list[tuple[object, ...]] = []

    class FakeMarkItDownInstance:
        def convert_local(self, path: Path) -> SimpleNamespace:
            calls.append((path,))
            return SimpleNamespace(markdown="# converted")

    monkeypatch.setattr(converter, "_create_markitdown", lambda: FakeMarkItDownInstance())

    assert converter.convert_to_markdown(file_path) == "# converted"
    assert calls == [(file_path,)]


def test_convert_to_markdown_rejects_unsupported_extension(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="未対応のファイル形式"):
        converter.convert_to_markdown(tmp_path / "notes.txt")
