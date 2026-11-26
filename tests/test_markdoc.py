from pathlib import Path

from docx import Document

from markdoc import collect_marks, mark_all, mark_document

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


def _mark(needle: str) -> dict:
    return {"text": needle, "severity": "warn", "message": "шифр без года"}


def test_mark_document_respects_right_boundary(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    doc.add_paragraph("Принят ГОСТ 27751-2014, ранее упоминался ГОСТ 27751.")
    doc.save(src)

    stats = mark_document(src, tmp_path / "out" / "a.docx", [_mark("ГОСТ 27751")])
    assert stats["comments"] == 1

    marked = Document(tmp_path / "out" / "a.docx")
    highlighted = [r.text for r in marked.paragraphs[0].runs if r.font.highlight_color]
    assert "".join(highlighted) == "ГОСТ 27751"


def test_mark_document_marks_every_occurrence_in_paragraph(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    doc.add_paragraph("ГОСТ 27751 и снова ГОСТ 27751 в одном абзаце.")
    doc.save(src)

    stats = mark_document(src, tmp_path / "out" / "a.docx", [_mark("ГОСТ 27751")])
    assert stats["comments"] == 2


def test_mark_document_walks_nested_tables(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    outer = doc.add_table(rows=1, cols=1)
    inner = outer.cell(0, 0).add_table(rows=1, cols=1)
    inner.cell(0, 0).text = "Применён ГОСТ 27751"
    doc.save(src)

    stats = mark_document(src, tmp_path / "out" / "a.docx", [_mark("ГОСТ 27751")])
    assert stats["comments"] == 1
