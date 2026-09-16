from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium

OCR_MAX_PAGES = 2
OCR_LANGUAGES = ["ja"]
TEXT_LAYER_MIN_CHARS = 50


def has_text_layer(file_path: Path) -> bool:
    pdf = pdfium.PdfDocument(str(file_path))
    character_count = 0
    try:
        for page_index in range(min(len(pdf), OCR_MAX_PAGES)):
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
def _create_ocr_converter() -> Any:
    # Delay the heavyweight imports until OCR is requested. This also keeps the
    # inexpensive text-layer check usable without loading OCR models.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=EasyOcrOptions(lang=OCR_LANGUAGES, use_gpu=False),
        do_table_structure=False,
        do_picture_description=False,
        generate_page_images=False,
        generate_picture_images=False,
    )
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        },
    )


def _export_to_markdown(document: Any) -> str:
    from docling_core.types.doc import ImageRefMode

    return document.export_to_markdown(image_mode=ImageRefMode.PLACEHOLDER)


def ocr_to_markdown(file_path: Path) -> str:
    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"OCR対象はPDFのみです: {file_path.suffix}")

    converter = _create_ocr_converter()
    result = converter.convert(file_path, page_range=(1, OCR_MAX_PAGES))
    return _export_to_markdown(result.document)
