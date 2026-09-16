# STRUCTURE.md

Directory layout of `doc-title-renamer`.

```
doc-title-renamer/
├── README.md               # User-facing documentation
├── LICENSE                  # MIT License
├── NOTICE.md                # Third-party license notices for direct dependencies
├── CLAUDE.md                # Guidelines/constraints for AI coding agents (kept at the repo
│                            #   root because Claude Code auto-loads it from there)
├── pyproject.toml            # Package definition and entry point for `uvx` execution
├── docs/
│   ├── DESIGN.md              # Functional and non-functional requirements
│   ├── STRUCTURE.md          # This file
│   └── TEST.md                # Test policy and coverage status
├── src/
│   └── doc_title_renamer/
│       ├── __init__.py
│       ├── cli.py             # CLI entry point; dispatches the `rename-only` / `organize` subcommands
│       ├── scanner.py          # Enumerates target files for a single file or a folder (with a stable sort)
│       ├── converter.py        # Converts docx/xlsx/pptx/PDF to Markdown via Docling
│       ├── ocr.py              # OCR for scanned PDFs (EasyOCR, first 2 pages only)
│       ├── md_cleaner.py       # Markdown cleaning (whitespace compaction, CJK spacing fixes, NFKC normalization, noise-line removal)
│       ├── date_parser.py      # Japanese-era-to-Gregorian conversion; validation of the LLM's issue date
│       ├── llm_client.py       # Requests a title/issue-date guess from a local LLM (OpenAI-compatible API) via structured JSON output
│       ├── namer.py            # Filename/folder-name generation (`YYYYMMDD_title` / `YYYYMM`), sanitization, collision avoidance
│       └── renamer.py          # Actual rename/move operations (batch collisions, no-op detection, per-file error skipping)
└── tests/
    ├── helpers.py              # Minimal PDF-generation helpers for tests
    ├── test_scanner.py
    ├── test_converter.py
    ├── test_ocr.py
    ├── test_cli.py
    ├── test_md_cleaner.py
    ├── test_date_parser.py
    ├── test_llm_client.py
    ├── test_namer.py
    └── test_renamer.py
```

## Module responsibilities

- `cli.py`: parses command-line arguments, dispatches the `rename-only` /
  `organize` subcommands, orchestrates the overall run, and handles `--yes`
  (skipping the confirmation prompt).
- `scanner.py`: determines whether the input path is a file or a folder and
  returns the target files in a stable order (ascending path order, etc.),
  excluding subfolders and Office temporary files starting with `~$`. Also
  provides `resolve_organize_base_dir`, which resolves where the `YYYYMM`
  folder should be created for `organize` mode (the given folder itself, or
  the parent folder when a single file is given).
- `converter.py`: converts docx/xlsx/pptx/PDF (with a text layer) to
  Markdown via Docling.
- `ocr.py`: converts PDFs without a text layer to Markdown via EasyOCR
  (first 2 pages only, image placeholders, no table analysis, language
  `ja`).
- `md_cleaner.py`: cleans Markdown right after extraction and before it is
  passed to the LLM (whitespace/newline compaction, removal of stray
  spaces between CJK characters, Unicode normalization (NFKC), removal of
  ruled-line-style noise lines, thinning of image placeholders, removal of
  control characters).
- `date_parser.py`: converts Japanese era dates to the Gregorian calendar
  (normalization before the LLM sees them), and **validates the issue date
  returned by the LLM** (whether it's a real calendar date, not too far in
  the future, etc.). The final decision between the LLM's guess and the
  creation-date fallback is made in `llm_client.py`.
- `llm_client.py`: communicates with the local LLM (OpenAI-compatible API;
  LM Studio, Ollama, etc.) using the standard library's `urllib.request`,
  sending the converted and cleaned Markdown (first ~5000 characters) and
  retrieving a candidate title and issue date as structured JSON output.
  Resolves the model via `/v1/models` when none is specified. Also handles
  response validation and fallback decisions on parse failure (no extra
  HTTP client library such as `openai` is used). When building the prompt,
  it separates the system instructions (the fixed task and output format
  only) from the document excerpt (data wrapped in a delimiter marker) and
  states explicitly that embedded instructions in the document must not be
  followed (prompt-injection countermeasures; see
  [DESIGN.md](DESIGN.md) section 4.6.1).
- `namer.py`: computes the new name per the naming rules (`YYYYMMDD_title.ext`
  / `YYYYMM`), applies Windows sanitization (forbidden characters, trailing
  period/space, control characters), truncates based on character/path
  length, and assigns numeric suffixes on collisions (considering both
  existing files and duplicates within the same batch).
- `renamer.py`: performs the actual filesystem operations (rename/move).
  Treats a destination identical to the current path as a no-op, and on a
  failure (e.g. a file lock) skips only that file and logs it.
