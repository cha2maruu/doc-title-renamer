# TEST.md

Test policy and instructions for running the test suite for this project.

## Policy

- Pure logic (filesystem judgments, string processing, naming rules,
  collision avoidance — anything that doesn't depend on external services
  or heavyweight libraries) is covered by **automated pytest tests** under
  `tests/`.
- Actual conversion/OCR via MarkItDown/RapidOCR, real requests to a local
  LLM (LM Studio, Ollama, etc. via an OpenAI-compatible API), and full
  end-to-end runs against real documents depend on the runtime environment
  (model/external process) and are instead verified through **manual
  testing with sample files**. MarkItDown's and RapidOCR's configuration
  and call sites are covered by unit tests using fake modules/mocks; the
  quality of real-file conversion/OCR is verified manually.
- `markitdown` and `rapidocr` (+ `onnxruntime`) are the runtime conversion/
  OCR dependencies; unlike the previous Docling/EasyOCR (PyTorch-based)
  setup, they are ONNX Runtime based and lighter to install, but their
  imports are still deferred in `converter.py`/`ocr.py` and replaced with
  fake modules in unit tests, so the full suite does not require them to be
  installed (see "Running tests" below).
- Test fixtures (e.g. PDFs) are generated on the fly by helper code such as
  `tests/helpers.py`, without adding extra dependencies (binary sample
  files are not committed to the repository).

## Test coverage by module

| Module | Automated tests | Notes |
|---|---|---|
| `scanner.py` | [x] `tests/test_scanner.py` | File/folder detection, extension case-insensitivity, `~$` exclusion, non-recursive scanning, stable sort, base-directory resolution for `organize` |
| `ocr.py` | [x] `tests/test_ocr.py` | Boundary check of the text-layer threshold (50 characters) and all-pages coverage using minimal PDFs generated with `pypdfium2`. Verifies the RapidOCR engine is built with PP-OCRv6 small (Det/Rec) + PP-OCRv4 mobile (Cls), all on ONNX Runtime, via a fake `rapidocr` module; verifies OCR runs on every page (no page-count limit) and detection-order text assembly, via mocks |
| `cli.py` | [x] `tests/test_cli.py` | Zero-target case, orchestration of conversion/OCR/LLM/naming/moving, fallbacks, `organize`, y/n confirmation / non-TTY / EOF / `--yes`, `--force-ocr` (forces OCR despite a detected text layer, skips the text-layer check, has no effect on non-PDF files), pre-flight connection failure, per-file failure, re-validation just before execution, exit codes, per-file `[i/N]` progress line ordering, preview/results two-/three-column table rendering (destination folder, date, title, model omitted; `organize` mode's `YYYYMM` folder also omitted) — all verified via mocks |
| `converter.py` | [x] `tests/test_converter.py` | Supported formats, OCR disabled for normal PDFs, Markdown conversion (`enable_plugins=False`) — verified via a fake `markitdown` module/mocks |
| `md_cleaner.py` | [x] `tests/test_md_cleaner.py` | Whitespace/CJK-spacing/blank-line compaction, NFKC normalization, noise-line removal, thinning of consecutive MarkItDown image placeholders (keeping non-adjacent ones), invisible characters |
| `date_parser.py` | [x] `tests/test_date_parser.py` | All Japanese eras and their first year, valid dates, the one-year-ahead future-date threshold, leap days |
| `llm_client.py` | [x] `tests/test_llm_client.py` | Real network calls are verified manually. Model resolution, structured prompting, era conversion, JSON validation, retry, unsupported `response_format`, and connection failure — verified via `urllib.request` mocks |
| `namer.py` | [x] `tests/test_namer.py` | Windows sanitization, the 40-character boundary, final filename/full-path length, collision avoidance against existing files and within a batch, no-op detection |
| `renamer.py` | [x] `tests/test_renamer.py` | Rename, move, parent-folder creation, no-op, overwrite prevention, and per-file failure continuation — verified with `tmp_path` |
| End-to-end flow (sample files, real local LLM) | [ ] Manual only | Verified on Windows with Ollama (`qwen3:8b`) across all supported formats (docx/xlsx/pptx/PDF with a text layer/scanned PDF) |

## Running tests

### Lightweight (recommended)

MarkItDown/RapidOCR-related imports are deferred until actual conversion
and are replaced with fake modules in unit tests, so `markitdown`/
`rapidocr`/`onnxruntime` do not need to be installed to run the suite.

```bash
python -m venv .venv
./.venv/Scripts/pip install pytest pypdfium2
PYTHONPATH=src ./.venv/Scripts/python -m pytest tests/ -q
```

### With the full project dependencies

When adding tests that need the real MarkItDown/RapidOCR stack (e.g. for
manual real-file verification), run them via `uv`'s dev dependency group
(`[dependency-groups] dev` in `pyproject.toml`).

```bash
uv run --group dev pytest tests/ -q
```

## Notes for writing tests

- Name test files 1:1 with the module under test: `tests/test_<module>.py`.
- Use the `tmp_path` fixture to create minimal test data on a real
  filesystem for each test.
- Explicitly test boundary values (character thresholds, filename-length
  limits, etc.).
- Don't hardcode requirement-derived constants (e.g.
  `TEXT_LAYER_MIN_CHARS`, `TITLE_MAX_LENGTH`) in test code — import them
  from the module under test, so tests keep tracking [DESIGN.md](DESIGN.md)
  if those values change.
