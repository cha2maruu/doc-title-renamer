from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import pypdfium2 as pdfium

OCR_RENDER_SCALE = 2.0
TEXT_LAYER_MIN_CHARS = 50


def has_text_layer(file_path: Path) -> bool:
    pdf = pdfium.PdfDocument(str(file_path))
    character_count = 0
    try:
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range()
                    character_count += len(re.sub(r"\s+", "", text))
                finally:
                    textpage.close()
            finally:
                page.close()
    finally:
        pdf.close()

    return character_count >= TEXT_LAYER_MIN_CHARS


@lru_cache(maxsize=1)
def _create_ocr_engine() -> Any:
    # Delay importing RapidOCR and loading its models until OCR is requested.
    # This keeps the inexpensive text-layer check usable on its own.
    from rapidocr import (
        EngineType,
        LangCls,
        LangDet,
        LangRec,
        ModelType,
        OCRVersion,
        RapidOCR,
    )

    return RapidOCR(
        params={
            # RapidOCR's own logger defaults to "info" and prints one
            # "[INFO] Using engine_name: ..." / "Using <model path>" line per
            # Det/Cls/Rec engine at construction time. That's noise on top of
            # this tool's own progress output, so it's raised to "warning"
            # via RapidOCR's own config key (setting the logger directly
            # from here wouldn't stick: RapidOCR.__init__ always re-applies
            # Global.log_level to its logger *after* construction starts).
            # Actual warnings/errors from RapidOCR remain visible.
            "Global.log_level": "warning",
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet.CH,
            "Det.model_type": ModelType.SMALL,
            "Det.ocr_version": OCRVersion.PPOCRV6,
            "Cls.engine_type": EngineType.ONNXRUNTIME,
            "Cls.lang_type": LangCls.CH,
            "Cls.model_type": ModelType.MOBILE,
            "Cls.ocr_version": OCRVersion.PPOCRV4,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.lang_type": LangRec.CH,
            "Rec.model_type": ModelType.SMALL,
            "Rec.ocr_version": OCRVersion.PPOCRV6,
        }
    )


def _ocr_result_to_text(result: Any) -> str:
    """Return detected text lines in RapidOCR's reading order."""
    texts = getattr(result, "txts", None)
    if not texts:
        return ""
    return "\n".join(text.strip() for text in texts if text.strip())


def ocr_to_markdown(
    file_path: Path, on_page: Callable[[int, int], None] | None = None
) -> str:
    """Run OCR over every page of ``file_path`` and return assembled Markdown.

    ``on_page``, if given, is called once with ``(0, total_pages)`` before
    OCR starts, and again after each page finishes with
    ``(page_number, total_pages)`` (1-indexed), so callers can report
    progress on long-running scans without this module knowing anything
    about how that progress should be displayed.
    """
    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"OCR対象はPDFのみです: {file_path.suffix}")

    engine = _create_ocr_engine()
    pdf = pdfium.PdfDocument(str(file_path))
    page_texts: list[str] = []
    try:
        total_pages = len(pdf)
        if on_page:
            on_page(0, total_pages)
        for page_index in range(total_pages):
            page = pdf[page_index]
            try:
                bitmap = page.render(scale=OCR_RENDER_SCALE)
                try:
                    result = engine(bitmap.to_numpy())
                finally:
                    bitmap.close()
            finally:
                page.close()

            text = _ocr_result_to_text(result)
            if text:
                page_texts.append(text)
            if on_page:
                on_page(page_index + 1, total_pages)
    finally:
        pdf.close()

    # A blank line preserves page boundaries while remaining plain Markdown.
    return "\n\n".join(page_texts)
