from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".pdf"}


@lru_cache(maxsize=1)
def _create_document_converter() -> Any:
    # Keep Docling imports local so lightweight modules/tests can be used without
    # loading the document-conversion stack until conversion is actually needed.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pdf_options = PdfPipelineOptions(do_ocr=False)
    return DocumentConverter(
        allowed_formats=[
            InputFormat.DOCX,
            InputFormat.XLSX,
            InputFormat.PPTX,
            InputFormat.PDF,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
        },
    )


def _export_to_markdown(document: Any) -> str:
    from docling_core.types.doc import ImageRefMode

    return document.export_to_markdown(image_mode=ImageRefMode.PLACEHOLDER)


def convert_to_markdown(file_path: Path) -> str:
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"未対応のファイル形式です: {file_path.suffix}")

    converter = _create_document_converter()
    result = converter.convert(file_path)
    return _export_to_markdown(result.document)
