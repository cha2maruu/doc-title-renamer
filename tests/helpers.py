from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace


class FakeMarkItDown:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


def install_fake_markitdown(monkeypatch: object) -> SimpleNamespace:
    markitdown = ModuleType("markitdown")
    markitdown.MarkItDown = FakeMarkItDown  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "markitdown", markitdown)  # type: ignore[attr-defined]

    return SimpleNamespace(MarkItDown=FakeMarkItDown)


def install_fake_rapidocr(monkeypatch: object) -> SimpleNamespace:
    rapidocr = ModuleType("rapidocr")

    class FakeEnum:
        ONNXRUNTIME = "onnxruntime"
        CH = "ch"
        SMALL = "small"
        MOBILE = "mobile"
        PPOCRV4 = "PP-OCRv4"
        PPOCRV6 = "PP-OCRv6"

    class FakeRapidOCR:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    rapidocr.EngineType = FakeEnum  # type: ignore[attr-defined]
    rapidocr.LangCls = FakeEnum  # type: ignore[attr-defined]
    rapidocr.LangDet = FakeEnum  # type: ignore[attr-defined]
    rapidocr.LangRec = FakeEnum  # type: ignore[attr-defined]
    rapidocr.ModelType = FakeEnum  # type: ignore[attr-defined]
    rapidocr.OCRVersion = FakeEnum  # type: ignore[attr-defined]
    rapidocr.RapidOCR = FakeRapidOCR  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rapidocr", rapidocr)  # type: ignore[attr-defined]

    return SimpleNamespace(Enum=FakeEnum, RapidOCR=FakeRapidOCR)


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
