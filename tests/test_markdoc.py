from pathlib import Path

from docx import Document

from markdoc import collect_marks, mark_all

FILES = ["01-ПЗ-АТЛАС.docx", "02-АР-АТЛАС.docx", "03-КР-АТЛАС.docx"]
CODE = "СН 5.03.01-2020"


def _result(files: list[str]) -> dict:
    return {"findings": [{
        "severity": "warn",
        "category": "нормы",
        "file": ", ".join(files),
        "files": files,
        "page": None,
        "message": f"шифр {CODE}: нет в реестре",
        "norm": CODE,
        "action": "",
    }]}


def _make_docs(root: Path) -> None:
    for name in FILES:
        doc = Document()
        doc.add_paragraph(f"В проекте применён шифр {CODE}.")
        doc.save(root / name)


def test_collect_marks_uses_all_files_of_folded_finding(tmp_path):
    _make_docs(tmp_path)
    marks = collect_marks(_result(FILES), tmp_path)
    assert sorted(marks) == sorted(FILES)
    for name in FILES:
        assert marks[name][0]["text"] == CODE


def test_collect_marks_falls_back_to_comma_list(tmp_path):
    _make_docs(tmp_path)
    result = _result(FILES)
    result["findings"][0].pop("files")
    marks = collect_marks(result, tmp_path)
    assert sorted(marks) == sorted(FILES)


def test_mark_all_comments_every_affected_file(tmp_path):
    _make_docs(tmp_path)
    reports = mark_all(_result(FILES), tmp_path, tmp_path / "out")
    by_file = {r["file"]: r for r in reports}
    assert sorted(by_file) == sorted(FILES)
    for name in FILES:
        assert by_file[name]["comments"] >= 1
        marked = Document(tmp_path / "out" / name)
        assert marked.comments, f"нет комментариев в {name}"
