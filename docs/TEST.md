# TEST.md

Test policy and instructions for running the test suite for this project.

## Policy

- Pure logic (filesystem judgments, string processing, naming rules,
  collision avoidance — anything that doesn't depend on external services
  or heavyweight libraries) is covered by **automated pytest tests** under
  `tests/`.
- Actual conversion/OCR via Docling/EasyOCR, real requests to a local LLM
  (LM Studio, Ollama, etc. via an OpenAI-compatible API), and full
  end-to-end runs against real documents depend on the runtime environment
  (GPU/model/external process) and are instead verified through **manual
  testing with sample files**. Docling's configuration and call sites are
  covered by unit tests using fake modules/mocks; the quality of real-file
  conversion is verified manually.
- `docling` and `easyocr` are heavyweight packages that take a long time to
  install. Modules that don't import them directly are tested without
  installing them (see "Running tests" below).
- Test fixtures (e.g. PDFs) are generated on the fly by helper code such as
  `tests/helpers.py`, without adding extra dependencies (binary sample
  files are not committed to the repository).

## Test coverage by module

| Module | Automated tests | Notes |
|---|---|---|
| `scanner.py` | [x] `tests/test_scanner.py` | File/folder detection, extension case-insensitivity, `~$` exclusion, non-recursive scanning, stable sort, base-directory resolution for `organize` |
| `ocr.py` | [x] `tests/test_ocr.py` | Boundary check of the text-layer threshold (50 characters) using minimal PDFs generated with `pypdfium2`. Verifies EasyOCR (`ja`, CPU) via a fake Docling module, disabled table/image analysis, image placeholders, and the first-2-pages limit passed to the conversion API |
| `cli.py` | [x] `tests/test_cli.py` | Zero-target case, orchestration of conversion/OCR/LLM/naming/moving, fallbacks, `organize`, y/n confirmation / non-TTY / EOF / `--yes`, pre-flight connection failure, per-file failure, re-validation just before execution, exit codes — all verified via mocks |
| `converter.py` | [x] `tests/test_converter.py` | Supported formats, OCR disabled for normal PDFs, Markdown conversion, image placeholders — verified via a fake Docling module/mocks |
| `md_cleaner.py` | [x] `tests/test_md_cleaner.py` | Whitespace/CJK-spacing/blank-line compaction, NFKC normalization, noise-line removal, image placeholders, invisible characters |
| `date_parser.py` | [x] `tests/test_date_parser.py` | All Japanese eras and their first year, valid dates, the one-year-ahead future-date threshold, leap days |
| `llm_client.py` | [x] `tests/test_llm_client.py` | Real network calls are verified manually. Model resolution, structured prompting, era conversion, JSON validation, retry, unsupported `response_format`, and connection failure — verified via `urllib.request` mocks |
| `namer.py` | [x] `tests/test_namer.py` | Windows sanitization, the 40-character boundary, final filename/full-path length, collision avoidance against existing files and within a batch, no-op detection |
| `renamer.py` | [x] `tests/test_renamer.py` | Rename, move, parent-folder creation, no-op, overwrite prevention, and per-file failure continuation — verified with `tmp_path` |
| End-to-end flow (sample files, real local LLM) | [ ] Manual only | Verified on Windows with Ollama (`qwen3:8b`) across all supported formats (docx/xlsx/pptx/PDF with a text layer/scanned PDF) |

## Running tests

### Lightweight (recommended)

Docling-related imports are deferred until actual conversion and are
replaced with fake modules in unit tests, so `docling`/`easyocr` do not
need to be installed to run the suite.

```bash
python -m venv .venv
./.venv/Scripts/pip install pytest pypdfium2
PYTHONPATH=src ./.venv/Scripts/python -m pytest tests/ -q
```

### With the full project dependencies

When adding tests that depend on Docling/EasyOCR (e.g. for `converter.py`),
run them via `uv`'s dev dependency group (`[dependency-groups] dev` in
`pyproject.toml`). The first run installs the full `docling`/`easyocr`
stack and takes a while.

```bash
uv run --group dev pytest tests/ -q
```

## Notes for writing tests

- Name test files 1:1 with the module under test: `tests/test_<module>.py`.
- Use the `tmp_path` fixture to create minimal test data on a real
  filesystem for each test.
- Explicitly test boundary values (character thresholds, page-count
  limits, filename-length limits, etc.).
- Don't hardcode requirement-derived constants (e.g.
  `TEXT_LAYER_MIN_CHARS`, `OCR_MAX_PAGES`, `TITLE_MAX_LENGTH`) in test
  code — import them from the module under test, so tests keep tracking
  [DESIGN.md](DESIGN.md) if those values change.
