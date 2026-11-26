from docx import Document

from markdoc import collect_marks, mark_document


def _doc(path, text):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(str(path))


def test_collect_marks_all_files_of_folded_finding(tmp_path):
    for name in ("a", "b", "c"):
        _doc(tmp_path / f"{name}.docx", "СНБ 2.04.02-2000")
    result = {"findings": [{
        "severity": "error", "category": "нормы", "file": "a, b, c",
        "files": ["a", "b", "c"], "message": "устарела",
        "norm": "СНБ 2.04.02-2000",
    }]}
    marks = collect_marks(result, tmp_path)
    assert set(marks) == {"a.docx", "b.docx", "c.docx"}
    assert all(m[0]["text"] == "СНБ 2.04.02-2000" for m in marks.values())


def test_mark_document_skips_longer_code_with_year(tmp_path):
    src = tmp_path / "in.docx"
    _doc(src, "Принят ГОСТ 27751-2014, ранее упоминался ГОСТ 27751.")
    dst = tmp_path / "out.docx"
    stats = mark_document(src, dst, [{
        "text": "ГОСТ 27751", "severity": "warn", "message": "шифр без года",
    }])
    assert stats["comments"] == 1

    doc = Document(str(dst))
    highlighted = [r.text for p in doc.paragraphs for r in p.runs
                   if r.font.highlight_color]
    assert highlighted == ["ГОСТ 27751"]


def test_mark_document_finds_nested_table(tmp_path):
    src = tmp_path / "nested.docx"
    doc = Document()
    outer = doc.add_table(rows=1, cols=1)
    inner = outer.cell(0, 0).add_table(rows=1, cols=1)
    inner.cell(0, 0).text = "СНБ 2.04.02-2000"
    doc.save(str(src))

    dst = tmp_path / "nested-out.docx"
    stats = mark_document(src, dst, [{
        "text": "СНБ 2.04.02-2000", "severity": "error", "message": "устарела",
    }])
    assert stats["comments"] == 1
