from pathlib import Path
from types import SimpleNamespace

import pytest

from doc_title_renamer import converter

from helpers import install_fake_docling


def test_create_document_converter_disables_ocr_for_regular_pdf(monkeypatch) -> None:
    fake = install_fake_docling(monkeypatch)
    converter._create_document_converter.cache_clear()

    try:
        document_converter = converter._create_document_converter()

        assert document_converter.kwargs["allowed_formats"] == [
            fake.InputFormat.DOCX,
            fake.InputFormat.XLSX,
            fake.InputFormat.PPTX,
            fake.InputFormat.PDF,
        ]
        pdf_format = document_converter.kwargs["format_options"][fake.InputFormat.PDF]
        assert pdf_format.kwargs["pipeline_options"].kwargs == {"do_ocr": False}
    finally:
        converter._create_document_converter.cache_clear()


def test_export_to_markdown_uses_image_placeholder(monkeypatch) -> None:
    fake = install_fake_docling(monkeypatch)
    calls: list[dict[str, object]] = []

    class FakeDocument:
        def export_to_markdown(self, **kwargs: object) -> str:
            calls.append(kwargs)
            return "markdown"

    assert converter._export_to_markdown(FakeDocument()) == "markdown"
    assert calls == [{"image_mode": fake.ImageRefMode.PLACEHOLDER}]


def test_convert_to_markdown_uses_docling_result(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "document.DOCX"
    document = object()
    calls: list[tuple[object, ...]] = []

    class FakeConverter:
        def convert(self, source: Path) -> SimpleNamespace:
            calls.append((source,))
            return SimpleNamespace(document=document)

    monkeypatch.setattr(converter, "_create_document_converter", FakeConverter)
    monkeypatch.setattr(
        converter,
        "_export_to_markdown",
        lambda converted_document: "# converted"
        if converted_document is document
        else pytest.fail("unexpected document"),
    )

    assert converter.convert_to_markdown(file_path) == "# converted"
    assert calls == [(file_path,)]


def test_convert_to_markdown_rejects_unsupported_extension(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="未対応のファイル形式"):
        converter.convert_to_markdown(tmp_path / "notes.txt")
