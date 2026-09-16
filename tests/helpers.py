from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace


class FakeOptions:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class FakeDocumentConverter:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class FakeInputFormat:
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    PDF = "pdf"


class FakeImageRefMode:
    PLACEHOLDER = object()


def install_fake_docling(monkeypatch: object) -> SimpleNamespace:
    docling = ModuleType("docling")
    docling.__path__ = []  # type: ignore[attr-defined]
    datamodel = ModuleType("docling.datamodel")
    datamodel.__path__ = []  # type: ignore[attr-defined]
    base_models = ModuleType("docling.datamodel.base_models")
    pipeline_options = ModuleType("docling.datamodel.pipeline_options")
    document_converter = ModuleType("docling.document_converter")
    docling_core = ModuleType("docling_core")
    docling_core.__path__ = []  # type: ignore[attr-defined]
    core_types = ModuleType("docling_core.types")
    core_types.__path__ = []  # type: ignore[attr-defined]
    core_doc = ModuleType("docling_core.types.doc")

    base_models.InputFormat = FakeInputFormat  # type: ignore[attr-defined]
    pipeline_options.EasyOcrOptions = FakeOptions  # type: ignore[attr-defined]
    pipeline_options.PdfPipelineOptions = FakeOptions  # type: ignore[attr-defined]
    document_converter.DocumentConverter = (  # type: ignore[attr-defined]
        FakeDocumentConverter
    )
    document_converter.PdfFormatOption = FakeOptions  # type: ignore[attr-defined]
    core_doc.ImageRefMode = FakeImageRefMode  # type: ignore[attr-defined]

    modules = {
        "docling": docling,
        "docling.datamodel": datamodel,
        "docling.datamodel.base_models": base_models,
        "docling.datamodel.pipeline_options": pipeline_options,
        "docling.document_converter": document_converter,
        "docling_core": docling_core,
        "docling_core.types": core_types,
        "docling_core.types.doc": core_doc,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)  # type: ignore[attr-defined]

    return SimpleNamespace(
        DocumentConverter=FakeDocumentConverter,
        ImageRefMode=FakeImageRefMode,
        InputFormat=FakeInputFormat,
        Options=FakeOptions,
    )


def build_minimal_pdf(page_texts: list[str | None]) -> bytes:
    objects: list[tuple[int, bytes]] = []

    def content_stream_for(text: str | None) -> bytes:
        if text is None:
            body = b""
        else:
            escaped = (
                text.encode("latin-1", errors="replace")
                .replace(b"(", rb"\(")
                .replace(b")", rb"\)")
            )
            body = b"BT /F1 12 Tf 10 700 Td (" + escaped + b") Tj ET"
        return b"<< /Length " + str(len(body)).encode() + b" >>\nstream\n" + body + b"\nendstream"

    n_pages = len(page_texts)
    catalog_num = 1
    pages_num = 2
    font_num = 3
    page_nums = [4 + 2 * i for i in range(n_pages)]
    content_nums = [5 + 2 * i for i in range(n_pages)]

    kids = " ".join(f"{pn} 0 R" for pn in page_nums)
    objects.append((catalog_num, f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode()))
    objects.append((pages_num, f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode()))
    objects.append((font_num, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    for i, text in enumerate(page_texts):
        pn = page_nums[i]
        cn = content_nums[i]
        page_body = (
            f"<< /Type /Page /Parent {pages_num} 0 R /Resources << /Font << /F1 {font_num} 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {cn} 0 R >>"
        ).encode()
        objects.append((pn, page_body))
        objects.append((cn, content_stream_for(text)))

    objects.sort(key=lambda t: t[0])

    out = bytearray()
    out += b"%PDF-1.4\n"
    offsets: dict[int, int] = {}
    for num, body in objects:
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_offset = len(out)
    max_num = max(offsets) + 1
    out += f"xref\n0 {max_num}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, max_num):
        off = offsets.get(num, 0)
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {max_num} /Root {catalog_num} 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    ).encode()

    return bytes(out)
