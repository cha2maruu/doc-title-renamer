from pathlib import Path

from doc_title_renamer.scanner import resolve_organize_base_dir, resolve_targets


def test_resolve_targets_from_directory(tmp_path: Path) -> None:
    target_names = ["document.docx", "report.XLSX", "slides.pptx", "summary.pdf"]
    for name in target_names:
        (tmp_path / name).touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "~$sample.docx").touch()
    subfolder = tmp_path / "nested"
    subfolder.mkdir()
    (subfolder / "nested.pdf").touch()

    targets = resolve_targets(tmp_path)

    expected = sorted((tmp_path / name for name in target_names), key=lambda path: path.name)
    assert targets == expected


def test_resolve_targets_from_supported_file(tmp_path: Path) -> None:
    target = tmp_path / "document.pdf"
    target.touch()

    assert resolve_targets(target) == [target]


def test_resolve_targets_excludes_unsupported_and_office_temp_files(tmp_path: Path) -> None:
    unsupported = tmp_path / "notes.txt"
    office_temp = tmp_path / "~$sample.docx"
    unsupported.touch()
    office_temp.touch()

    assert resolve_targets(unsupported) == []
    assert resolve_targets(office_temp) == []


def test_resolve_organize_base_dir(tmp_path: Path) -> None:
    target = tmp_path / "document.pdf"
    target.touch()

    assert resolve_organize_base_dir(tmp_path) == tmp_path
    assert resolve_organize_base_dir(target) == tmp_path
