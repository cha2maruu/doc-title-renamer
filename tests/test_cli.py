import builtins
import datetime
from pathlib import Path

import pytest

from doc_title_renamer import cli
from doc_title_renamer.llm_client import LLMConnectionError, TitleGuess
from doc_title_renamer.renamer import RenameResult


def _configure_success(monkeypatch, *, title: str = "見積書") -> None:
    monkeypatch.setattr(
        cli.llm_client, "resolve_model", lambda url, model, timeout=None: "test-model"
    )
    monkeypatch.setattr(
        cli.llm_client, "check_connection", lambda url, timeout=None: None
    )
    monkeypatch.setattr(cli.ocr, "has_text_layer", lambda path: True)
    monkeypatch.setattr(cli.converter, "convert_to_markdown", lambda path: " markdown ")
    monkeypatch.setattr(cli.md_cleaner, "clean_markdown", lambda text: "cleaned")
    monkeypatch.setattr(
        cli.llm_client,
        "guess_title_and_date",
        lambda markdown, url, model, timeout=None: TitleGuess(
            title, datetime.date(2026, 4, 15), model
        ),
    )


def test_run_returns_ok_when_no_targets_exist(tmp_path: Path, capsys) -> None:
    args = cli.build_parser().parse_args(["rename-only", str(tmp_path)])

    exit_code = cli.run(args)

    captured = capsys.readouterr()
    assert "対象ファイルが見つかりませんでした。" in captured.out
    assert exit_code == cli.EXIT_OK


def test_run_yes_executes_complete_pipeline(monkeypatch, tmp_path: Path, capsys) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(tmp_path), "--yes"])
    _configure_success(monkeypatch)
    calls: list[list[tuple[Path, Path]]] = []

    def fake_apply(plan: list[tuple[Path, Path]]) -> list[RenameResult]:
        calls.append(plan)
        return [RenameResult(src, dst, True) for src, dst in plan]

    monkeypatch.setattr(cli.renamer, "apply_plan", fake_apply)
    monkeypatch.setattr(
        builtins,
        "input",
        lambda prompt: (_ for _ in ()).throw(AssertionError("prompted")),
    )

    exit_code = cli.run(args)

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_OK
    assert calls == [[(source, tmp_path / "20260415_見積書.pdf")]]
    assert "変更予定:" in captured.out
    assert "実行結果:" in captured.out
    assert "test-model" in captured.out


def test_run_uses_ocr_for_scanned_pdf(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source), "--yes"])
    _configure_success(monkeypatch)
    monkeypatch.setattr(cli.ocr, "has_text_layer", lambda path: False)
    monkeypatch.setattr(cli.ocr, "ocr_to_markdown", lambda path: "ocr markdown")
    monkeypatch.setattr(
        cli.converter,
        "convert_to_markdown",
        lambda path: (_ for _ in ()).throw(AssertionError("converter called")),
    )
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: [RenameResult(src, dst, True) for src, dst in plan],
    )

    assert cli.run(args) == cli.EXIT_OK


def test_run_n_does_not_apply_plan(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source)])
    _configure_success(monkeypatch)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    answers = iter(["invalid", "N"])
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: (_ for _ in ()).throw(AssertionError("apply_plan called")),
    )

    assert cli.run(args) == cli.EXIT_OK


def test_run_y_applies_plan_after_retrying_invalid_input(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source)])
    _configure_success(monkeypatch)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    answers = iter(["?", "Y"])
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    applied: list[list[tuple[Path, Path]]] = []

    def fake_apply(plan: list[tuple[Path, Path]]) -> list[RenameResult]:
        applied.append(plan)
        return [RenameResult(src, dst, True) for src, dst in plan]

    monkeypatch.setattr(cli.renamer, "apply_plan", fake_apply)

    assert cli.run(args) == cli.EXIT_OK
    assert applied


def test_run_eof_does_not_apply_plan(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source)])
    _configure_success(monkeypatch)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        builtins,
        "input",
        lambda prompt: (_ for _ in ()).throw(EOFError()),
    )
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: (_ for _ in ()).throw(AssertionError("apply_plan called")),
    )

    assert cli.run(args) == cli.EXIT_OK


def test_run_non_tty_does_not_apply_plan(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source)])
    _configure_success(monkeypatch)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: (_ for _ in ()).throw(AssertionError("apply_plan called")),
    )

    assert cli.run(args) == cli.EXIT_OK


def test_run_returns_aborted_when_lm_studio_is_unavailable(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source), "--yes"])
    monkeypatch.setattr(
        cli.llm_client,
        "resolve_model",
        lambda url, model, timeout=None: (_ for _ in ()).throw(
            LLMConnectionError("offline")
        ),
    )

    assert cli.run(args) == cli.EXIT_ABORTED
    assert "事前確認に失敗" in capsys.readouterr().err


def test_run_checks_connection_when_model_is_explicit(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(
        ["rename-only", str(source), "--llm-model", "chosen", "--yes"]
    )
    _configure_success(monkeypatch)
    checked: list[str] = []
    monkeypatch.setattr(
        cli.llm_client, "check_connection", lambda url, timeout=None: checked.append(url)
    )
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: [RenameResult(src, dst, True) for src, dst in plan],
    )

    assert cli.run(args) == cli.EXIT_OK
    assert checked == [cli.DEFAULT_LLM_URL]


def test_run_checks_connection_when_model_is_explicit_and_forwards_timeout(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(
        ["rename-only", str(source), "--llm-model", "chosen", "--llm-timeout", "5", "--yes"]
    )
    _configure_success(monkeypatch)
    checked: list[tuple[str, float | None]] = []
    monkeypatch.setattr(
        cli.llm_client,
        "check_connection",
        lambda url, timeout=None: checked.append((url, timeout)),
    )
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: [RenameResult(src, dst, True) for src, dst in plan],
    )

    assert cli.run(args) == cli.EXIT_OK
    assert checked == [(cli.DEFAULT_LLM_URL, 5.0)]


def test_run_returns_partial_failure_for_one_file_error(
    monkeypatch, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.docx"
    good = tmp_path / "good.docx"
    bad.touch()
    good.touch()
    args = cli.build_parser().parse_args(["rename-only", str(tmp_path), "--yes"])
    _configure_success(monkeypatch)

    def fake_convert(path: Path) -> str:
        if path == bad:
            raise PermissionError("cannot read")
        return "markdown"

    monkeypatch.setattr(cli.converter, "convert_to_markdown", fake_convert)
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: [RenameResult(src, dst, True) for src, dst in plan],
    )

    assert cli.run(args) == cli.EXIT_PARTIAL_FAILURE


def test_run_organize_uses_yyyymm_destination(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "document.docx"
    source.touch()
    args = cli.build_parser().parse_args(["organize", str(source), "--yes"])
    _configure_success(monkeypatch)
    captured_plan: list[tuple[Path, Path]] = []

    def fake_apply(plan: list[tuple[Path, Path]]) -> list[RenameResult]:
        captured_plan.extend(plan)
        return [RenameResult(src, dst, True) for src, dst in plan]

    monkeypatch.setattr(cli.renamer, "apply_plan", fake_apply)

    assert cli.run(args) == cli.EXIT_OK
    assert captured_plan == [
        (source, tmp_path / "202604" / "20260415_見積書.docx")
    ]


def test_run_uses_title_and_created_date_fallbacks(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "元ファイル.docx"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source), "--yes"])
    _configure_success(monkeypatch)
    monkeypatch.setattr(
        cli.llm_client,
        "guess_title_and_date",
        lambda markdown, url, model, timeout=None: TitleGuess(None, None, model),
    )
    monkeypatch.setattr(
        cli, "_created_date", lambda path: datetime.date(2025, 12, 3)
    )
    captured_plan: list[tuple[Path, Path]] = []

    def fake_apply(plan: list[tuple[Path, Path]]) -> list[RenameResult]:
        captured_plan.extend(plan)
        return [RenameResult(src, dst, True) for src, dst in plan]

    monkeypatch.setattr(cli.renamer, "apply_plan", fake_apply)

    assert cli.run(args) == cli.EXIT_OK
    assert captured_plan == [
        (source, tmp_path / "20251203_元ファイル.docx")
    ]


def test_run_skips_destination_created_after_preview(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(["rename-only", str(source)])
    _configure_success(monkeypatch)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)

    def confirm_and_change(prompt: str) -> str:
        (tmp_path / "20260415_見積書.pdf").touch()
        return "y"

    monkeypatch.setattr(builtins, "input", confirm_and_change)
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: [RenameResult(src, dst, True) for src, dst in plan],
    )

    assert cli.run(args) == cli.EXIT_PARTIAL_FAILURE


def test_main_maps_argument_parser_errors_to_invalid_args() -> None:
    assert cli.main(["unknown-command"]) == cli.EXIT_INVALID_ARGS


def test_llm_timeout_defaults_to_llm_client_constant(tmp_path: Path) -> None:
    args = cli.build_parser().parse_args(["rename-only", str(tmp_path)])

    assert args.llm_timeout == cli.llm_client.REQUEST_TIMEOUT_SECONDS


def test_run_rejects_non_positive_llm_timeout(tmp_path: Path, capsys) -> None:
    args = cli.build_parser().parse_args(
        ["rename-only", str(tmp_path), "--llm-timeout", "0"]
    )

    with pytest.raises(cli.ArgumentError, match="--llm-timeout"):
        cli.run(args)


def test_run_forwards_llm_timeout_to_guess_title_and_date(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "document.pdf"
    source.touch()
    args = cli.build_parser().parse_args(
        ["rename-only", str(source), "--llm-timeout", "5", "--yes"]
    )
    _configure_success(monkeypatch)
    calls: list[float | None] = []

    def fake_guess(markdown, url, model, timeout=None):
        calls.append(timeout)
        return TitleGuess("見積書", datetime.date(2026, 4, 15), model)

    monkeypatch.setattr(cli.llm_client, "guess_title_and_date", fake_guess)
    monkeypatch.setattr(
        cli.renamer,
        "apply_plan",
        lambda plan: [RenameResult(src, dst, True) for src, dst in plan],
    )

    assert cli.run(args) == cli.EXIT_OK
    assert calls == [5.0]
