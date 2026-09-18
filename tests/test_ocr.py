from pathlib import Path
from types import SimpleNamespace

import pytest

from doc_title_renamer import ocr
from doc_title_renamer.ocr import TEXT_LAYER_MIN_CHARS, has_text_layer

from helpers import build_minimal_pdf, install_fake_rapidocr


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


def test_has_text_layer_checks_all_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "third-page-text.pdf"
    write_pdf(pdf_path, [None, None, "A" * (TEXT_LAYER_MIN_CHARS + 1)])

    assert has_text_layer(pdf_path) is True


def test_create_ocr_engine_uses_ppocrv6_small_with_onnxruntime(monkeypatch) -> None:
    fake = install_fake_rapidocr(monkeypatch)
    ocr._create_ocr_engine.cache_clear()

    try:
        engine = ocr._create_ocr_engine()

        assert isinstance(engine, fake.RapidOCR)
        assert engine.kwargs["params"] == {
            "Global.log_level": "warning",
            "Det.engine_type": fake.Enum.ONNXRUNTIME,
            "Det.lang_type": fake.Enum.CH,
            "Det.model_type": fake.Enum.SMALL,
            "Det.ocr_version": fake.Enum.PPOCRV6,
            "Cls.engine_type": fake.Enum.ONNXRUNTIME,
            "Cls.lang_type": fake.Enum.CH,
            "Cls.model_type": fake.Enum.MOBILE,
            "Cls.ocr_version": fake.Enum.PPOCRV4,
            "Rec.engine_type": fake.Enum.ONNXRUNTIME,
            "Rec.lang_type": fake.Enum.CH,
            "Rec.model_type": fake.Enum.SMALL,
            "Rec.ocr_version": fake.Enum.PPOCRV6,
        }
    finally:
        ocr._create_ocr_engine.cache_clear()


def test_ocr_result_to_text_preserves_detection_order() -> None:
    result = SimpleNamespace(txts=("1行目", " 2行目 ", ""))

    assert ocr._ocr_result_to_text(result) == "1行目\n2行目"
    assert ocr._ocr_result_to_text(SimpleNamespace(txts=None)) == ""


def test_ocr_to_markdown_processes_all_pages(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "scan.pdf"
    write_pdf(file_path, [None, None, None])
    calls: list[object] = []
    results = iter(
        [
            SimpleNamespace(txts=("1ページ1行目", "1ページ2行目")),
            SimpleNamespace(txts=()),
            SimpleNamespace(txts=("3ページ1行目",)),
        ]
    )

    def fake_engine(image: object) -> SimpleNamespace:
        calls.append(image)
        return next(results)

    monkeypatch.setattr(ocr, "_create_ocr_engine", lambda: fake_engine)

    assert ocr.ocr_to_markdown(file_path) == (
        "1ページ1行目\n1ページ2行目\n\n3ページ1行目"
    )
    assert len(calls) == 3
    assert all(getattr(image, "ndim", None) == 3 for image in calls)


def test_ocr_to_markdown_rejects_non_pdf(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="OCR対象はPDFのみ"):
        ocr.ocr_to_markdown(tmp_path / "document.docx")
