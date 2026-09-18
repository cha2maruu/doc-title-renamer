from __future__ import annotations

import argparse
import datetime
import sys
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlparse

from doc_title_renamer import (
    converter,
    llm_client,
    md_cleaner,
    namer,
    ocr,
    renamer,
    scanner,
)

DEFAULT_LLM_URL = "http://localhost:1234/v1"
ALLOWED_LLM_HOSTS = {"localhost", "127.0.0.1"}

EXIT_OK = 0
EXIT_PARTIAL_FAILURE = 1
EXIT_ABORTED = 2
EXIT_INVALID_ARGS = 64


class ArgumentError(Exception):
    pass


@dataclass(frozen=True)
class PlannedFile:
    source: Path
    destination: Path
    issue_date: datetime.date
    title: str
    model: str


@dataclass(frozen=True)
class FailedFile:
    source: Path
    error: str
    issue_date: datetime.date | None = None
    title: str | None = None
    model: str | None = None


def _validate_llm_url(url: str) -> None:
    host = urlparse(url).hostname
    if host not in ALLOWED_LLM_HOSTS:
        raise ArgumentError(
            f"--llm-url にはlocalhostのみ指定できます（指定された値: {url}）"
        )


def _validate_llm_timeout(timeout: float) -> None:
    if timeout <= 0:
        raise ArgumentError(
            f"--llm-timeout には正の数値を指定してください（指定された値: {timeout}）"
        )


def _add_common_arguments(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("path", type=Path, help="対象のファイルまたはフォルダのパス")
    subparser.add_argument(
        "--llm-url",
        default=DEFAULT_LLM_URL,
        help=(
            f"ローカルLLM(OpenAI互換API)のエンドポイント（既定値: {DEFAULT_LLM_URL}。"
            "localhostのみ指定可。LM Studio以外を使う場合はここで変更する）"
        ),
    )
    subparser.add_argument(
        "--llm-model",
        default=None,
        help="使用するモデル名（省略時はローカルLLMのロード済みモデルから自動解決）",
    )
    subparser.add_argument(
        "--llm-timeout",
        type=float,
        default=llm_client.REQUEST_TIMEOUT_SECONDS,
        help=(
            "ローカルLLMへの1回あたりの問い合わせタイムアウト秒数（既定値: "
            f"{llm_client.REQUEST_TIMEOUT_SECONDS}秒。thinking対応モデル等、応答が"
            "遅い場合はここで延長する）"
        ),
    )
    subparser.add_argument(
        "--yes",
        action="store_true",
        help="確認プロンプトを省略し、変更前後の一覧を表示したうえで自動的に実行する",
    )
    subparser.add_argument(
        "--force-ocr",
        action="store_true",
        help=(
            "PDFのテキストレイヤー有無の自動判定を無視し、常にOCR（RapidOCR）で"
            "抽出する。テキストレイヤーはあるが内容が壊れている/意図と異なる"
            "PDFへの対処用（docx/xlsx/pptxには影響しない）"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doc-title-renamer",
        description=(
            "docx/xlsx/pptx/PDFの内容を要約し、日付とタイトルでファイル名・"
            "フォルダを自動整理するCLIツール"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    rename_parser = subparsers.add_parser(
        "rename-only", help="ファイル名の変更のみを行う（移動はしない）"
    )
    _add_common_arguments(rename_parser)

    organize_parser = subparsers.add_parser(
        "organize", help="ファイル名を変更し、YYYYMMフォルダへ整理する"
    )
    _add_common_arguments(organize_parser)

    return parser


def _created_date(path: Path) -> datetime.date:
    return datetime.datetime.fromtimestamp(path.stat().st_ctime).date()


def _extract_markdown(path: Path, force_ocr: bool = False) -> str:
    if path.suffix.lower() == ".pdf" and (force_ocr or not ocr.has_text_layer(path)):
        return ocr.ocr_to_markdown(path)
    return converter.convert_to_markdown(path)


def _destination_for(
    args: argparse.Namespace,
    source: Path,
    issue_date: datetime.date,
    new_name: str,
) -> Path:
    if args.command == "organize":
        base_dir = scanner.resolve_organize_base_dir(args.path)
        return base_dir / f"{issue_date:%Y%m}" / new_name
    return source.with_name(new_name)


def _resolve_plans(
    planned_files: list[PlannedFile],
) -> tuple[list[PlannedFile], list[FailedFile]]:
    remaining = planned_files
    failures: list[FailedFile] = []
    while remaining:
        try:
            resolved_paths = namer.resolve_collisions(
                [(item.source, item.destination) for item in remaining]
            )
        except namer.PathLengthError as exc:
            failed = next(
                (item for item in remaining if item.source == exc.source), None
            )
            if failed is None:
                raise
            failures.append(
                FailedFile(
                    failed.source,
                    str(exc),
                    failed.issue_date,
                    failed.title,
                    failed.model,
                )
            )
            remaining = [item for item in remaining if item is not failed]
            continue

        return (
            [
                replace(item, destination=destination)
                for item, (_, destination) in zip(remaining, resolved_paths)
            ],
            failures,
        )
    return [], failures


def _display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _pad_cell(text: str, width: int) -> str:
    return text + " " * (width - _display_width(text))


def _render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [
        max(_display_width(cell) for cell in [header, *(row[i] for row in rows)])
        for i, header in enumerate(headers)
    ]
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def format_row(cells: list[str]) -> str:
        return (
            "|" + "|".join(f" {_pad_cell(cell, w)} " for cell, w in zip(cells, widths)) + "|"
        )

    lines = [border, format_row(headers), border]
    lines.extend(format_row(row) for row in rows)
    lines.append(border)
    return lines


def _print_preview(planned_files: list[PlannedFile]) -> None:
    print("変更予定:")
    rows = [[item.source.name, item.destination.name] for item in planned_files]
    for line in _render_table(["元ファイル名", "変更ファイル名"], rows):
        print(line)


def _confirm() -> bool:
    if not sys.stdin.isatty():
        print("標準入力がTTYではないため、実行しません。")
        return False
    while True:
        try:
            answer = input("実行しますか? [y/n]: ").strip().lower()
        except EOFError:
            print("入力が終了したため、実行しません。")
            return False
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("y または n を入力してください。")


def _file_state(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _print_results(
    rename_results: list[renamer.RenameResult],
    failures: list[FailedFile],
) -> None:
    print("実行結果:")
    rows: list[list[str]] = []
    for result in rename_results:
        status = "成功（変更不要）" if result.no_op else "成功"
        if not result.success:
            status = f"失敗: {result.error}"
        rows.append([result.source.name, result.destination.name, status])
    for failure in failures:
        rows.append([failure.source.name, "-", f"失敗: {failure.error}"])
    for line in _render_table(["元ファイル名", "変更ファイル名", "結果"], rows):
        print(line)


def run(args: argparse.Namespace) -> int:
    _validate_llm_url(args.llm_url)
    _validate_llm_timeout(args.llm_timeout)

    if not args.path.exists():
        print(f"指定されたパスが見つかりません: {args.path}", file=sys.stderr)
        return EXIT_INVALID_ARGS

    targets = scanner.resolve_targets(args.path)
    if not targets:
        print("対象ファイルが見つかりませんでした。")
        return EXIT_OK

    try:
        model = llm_client.resolve_model(
            args.llm_url, args.llm_model, timeout=args.llm_timeout
        )
        if args.llm_model is not None:
            llm_client.check_connection(args.llm_url, timeout=args.llm_timeout)
    except (llm_client.LLMConnectionError, llm_client.LLMResponseError, OSError) as exc:
        print(f"ローカルLLMの事前確認に失敗しました: {exc}", file=sys.stderr)
        return EXIT_ABORTED

    print(f"使用モデル: {model}")

    planned_files: list[PlannedFile] = []
    failures: list[FailedFile] = []
    total = len(targets)
    for index, source in enumerate(targets, start=1):
        print(f"[{index}/{total}] {source.name} を解析中...", flush=True)
        issue_date: datetime.date | None = None
        title: str | None = None
        try:
            markdown = _extract_markdown(source, args.force_ocr)
            cleaned_markdown = md_cleaner.clean_markdown(markdown)
            guess = llm_client.guess_title_and_date(
                cleaned_markdown, args.llm_url, model, timeout=args.llm_timeout
            )
            issue_date = guess.issue_date or _created_date(source)
            title = guess.title or source.stem
            if not namer.sanitize_title(title):
                title = source.stem
            sanitized_title = namer.sanitize_title(title)
            if not sanitized_title:
                raise ValueError("有効なタイトルを生成できませんでした")
            new_name = namer.build_new_name(
                issue_date, sanitized_title, source.suffix
            )
            destination = _destination_for(args, source, issue_date, new_name)
            planned_files.append(
                PlannedFile(
                    source, destination, issue_date, sanitized_title, guess.model
                )
            )
        except Exception as exc:
            failures.append(FailedFile(source, str(exc), issue_date, title, model))

    planned_files, collision_failures = _resolve_plans(planned_files)
    failures.extend(collision_failures)
    if not planned_files:
        _print_results([], failures)
        return EXIT_PARTIAL_FAILURE if failures else EXIT_OK

    snapshots: dict[Path, tuple[int, int, int]] = {}
    ready_files: list[PlannedFile] = []
    for item in planned_files:
        try:
            snapshots[item.source] = _file_state(item.source)
        except OSError as exc:
            failures.append(
                FailedFile(
                    item.source, str(exc), item.issue_date, item.title, item.model
                )
            )
        else:
            ready_files.append(item)
    planned_files = ready_files

    if not planned_files:
        _print_results([], failures)
        return EXIT_PARTIAL_FAILURE

    _print_preview(planned_files)
    if not args.yes and not _confirm():
        print("実行をキャンセルしました。")
        return EXIT_OK

    executable: list[PlannedFile] = []
    for item in planned_files:
        try:
            if _file_state(item.source) != snapshots[item.source]:
                raise OSError("確認後に移動元ファイルの状態が変更されました")
            if item.source != item.destination and item.destination.exists():
                raise FileExistsError("確認後に移動先ファイルが作成されました")
        except OSError as exc:
            failures.append(
                FailedFile(
                    item.source, str(exc), item.issue_date, item.title, item.model
                )
            )
        else:
            executable.append(item)

    rename_results = renamer.apply_plan(
        [(item.source, item.destination) for item in executable]
    )
    _print_results(rename_results, failures)
    if failures or any(not result.success for result in rename_results):
        return EXIT_PARTIAL_FAILURE
    return EXIT_OK


def _force_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_console()

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_OK if exc.code == 0 else EXIT_INVALID_ARGS

    try:
        return run(args)
    except ArgumentError as exc:
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return EXIT_INVALID_ARGS


if __name__ == "__main__":
    sys.exit(main())
