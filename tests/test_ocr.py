from pathlib import Path
from types import SimpleNamespace

import pytest

from doc_title_renamer import ocr
from doc_title_renamer.ocr import OCR_MAX_PAGES, TEXT_LAYER_MIN_CHARS, has_text_layer

from helpers import build_minimal_pdf, install_fake_docling


def write_pdf(path: Path, page_texts: list[str | None]) -> None:
    path.write_bytes(build_minimal_pdf(page_texts))


def test_has_text_layer_with_sufficient_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text.pdf"
    write_pdf(pdf_path, ["A" * (TEXT_LAYER_MIN_CHARS + 1)])

    assert has_text_layer(pdf_path) is True


def test_has_text_layer_without_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    write_pdf(pdf_path, [None])

    assert has_text_layer(pdf_path) is False


def test_has_text_layer_at_character_count_boundary(tmp_path: Path) -> None:
    threshold_pdf = tmp_path / "threshold.pdf"
    below_threshold_pdf = tmp_path / "below-threshold.pdf"
    write_pdf(threshold_pdf, ["A" * TEXT_LAYER_MIN_CHARS])
    write_pdf(below_threshold_pdf, ["A" * (TEXT_LAYER_MIN_CHARS - 1)])

    assert has_text_layer(threshold_pdf) is True
    assert has_text_layer(below_threshold_pdf) is False


def test_has_text_layer_ignores_pages_after_ocr_limit(tmp_path: Path) -> None:
    pdf_path = tmp_path / "third-page-text.pdf"
    page_texts = [None] * OCR_MAX_PAGES + ["A" * (TEXT_LAYER_MIN_CHARS + 1)]
    write_pdf(pdf_path, page_texts)

    assert has_text_layer(pdf_path) is False


def test_create_ocr_converter_uses_fast_easyocr_settings(monkeypatch) -> None:
    fake = install_fake_docling(monkeypatch)
    ocr._create_ocr_converter.cache_clear()

    try:
        document_converter = ocr._create_ocr_converter()

        assert document_converter.kwargs["allowed_formats"] == [fake.InputFormat.PDF]
        pdf_format = document_converter.kwargs["format_options"][fake.InputFormat.PDF]
        pipeline = pdf_format.kwargs["pipeline_options"].kwargs
        assert pipeline["do_ocr"] is True
        assert pipeline["ocr_options"].kwargs == {
            "lang": ocr.OCR_LANGUAGES,
            "use_gpu": False,
        }
        assert pipeline["do_table_structure"] is False
        assert pipeline["do_picture_description"] is False
        assert pipeline["generate_page_images"] is False
        assert pipeline["generate_picture_images"] is False
    finally:
        ocr._create_ocr_converter.cache_clear()


def test_ocr_export_uses_image_placeholder(monkeypatch) -> None:
    fake = install_fake_docling(monkeypatch)
    calls: list[dict[str, object]] = []

    class FakeDocument:
        def export_to_markdown(self, **kwargs: object) -> str:
            calls.append(kwargs)
            return "markdown"

    assert ocr._export_to_markdown(FakeDocument()) == "markdown"
    assert calls == [{"image_mode": fake.ImageRefMode.PLACEHOLDER}]


def test_ocr_to_markdown_limits_docling_conversion_to_first_two_pages(
    monkeypatch, tmp_path: Path
) -> None:
    file_path = tmp_path / "scan.pdf"
    document = object()
    calls: list[tuple[Path, tuple[int, int]]] = []

    class FakeConverter:
        def convert(
            self, source: Path, *, page_range: tuple[int, int]
        ) -> SimpleNamespace:
            calls.append((source, page_range))
            return SimpleNamespace(document=document)

    monkeypatch.setattr(ocr, "_create_ocr_converter", FakeConverter)
    monkeypatch.setattr(
        ocr,
        "_export_to_markdown",
        lambda converted_document: "OCR result"
        if converted_document is document
        else pytest.fail("unexpected document"),
    )

    assert ocr.ocr_to_markdown(file_path) == "OCR result"
    assert calls == [(file_path, (1, OCR_MAX_PAGES))]


def test_ocr_to_markdown_rejects_non_pdf(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="OCR対象はPDFのみ"):
        ocr.ocr_to_markdown(tmp_path / "document.docx")
