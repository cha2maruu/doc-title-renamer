from pathlib import Path

from doc_title_renamer.renamer import apply_plan


def test_apply_plan_renames_file(tmp_path: Path) -> None:
    source = tmp_path / "old.pdf"
    destination = tmp_path / "new.pdf"
    source.write_text("content", encoding="utf-8")

    result = apply_plan([(source, destination)])[0]

    assert result.success
    assert destination.read_text(encoding="utf-8") == "content"
    assert not source.exists()


def test_apply_plan_moves_file_and_creates_parent_folder(tmp_path: Path) -> None:
    source = tmp_path / "old.docx"
    destination = tmp_path / "202604" / "new.docx"
    source.touch()

    result = apply_plan([(source, destination)])[0]

    assert result.success
    assert destination.is_file()


def test_apply_plan_treats_same_path_as_no_op(tmp_path: Path) -> None:
    source = tmp_path / "same.pdf"
    source.touch()

    result = apply_plan([(source, source)])[0]

    assert result.success
    assert result.no_op
    assert source.is_file()


def test_apply_plan_skips_failure_and_continues(monkeypatch, tmp_path: Path) -> None:
    locked = tmp_path / "locked.pdf"
    movable = tmp_path / "movable.pdf"
    locked.touch()
    movable.touch()
    original_rename = Path.rename

    def fake_rename(path: Path, target: Path) -> Path:
        if path == locked:
            raise PermissionError("locked")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fake_rename)

    results = apply_plan(
        [(locked, tmp_path / "locked-new.pdf"), (movable, tmp_path / "moved.pdf")]
    )

    assert not results[0].success
    assert "locked" in (results[0].error or "")
    assert results[1].success
    assert (tmp_path / "moved.pdf").exists()


def test_apply_plan_never_overwrites_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    destination = tmp_path / "destination.pdf"
    source.write_text("source", encoding="utf-8")
    destination.write_text("destination", encoding="utf-8")

    result = apply_plan([(source, destination)])[0]

    assert not result.success
    assert source.exists()
    assert destination.read_text(encoding="utf-8") == "destination"
