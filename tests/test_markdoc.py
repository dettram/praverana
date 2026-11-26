import hashlib

from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from markdoc import _split_run, collect_marks, mark_all, mark_document


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
    highlighted = [(r.text, r.font.highlight_color) for p in doc.paragraphs
                   for r in p.runs if r.font.highlight_color]
    assert highlighted == [("ГОСТ 27751", WD_COLOR_INDEX.YELLOW)]


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


def test_source_file_is_not_changed(tmp_path):
    src = tmp_path / "src.docx"
    _doc(src, "СНБ 2.04.02-2000")
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    mark_document(src, tmp_path / "dst.docx", [{
        "text": "СНБ 2.04.02-2000", "severity": "error", "message": "устарела",
    }])
    assert hashlib.sha256(src.read_bytes()).hexdigest() == before


def test_split_run_keeps_text(tmp_path):
    doc = Document()
    paragraph = doc.add_paragraph()
    run = paragraph.add_run("abcdef")
    left, right = _split_run(run, 2)
    assert left.text == "ab"
    assert right.text == "cdef"


def test_limits_three_per_code_and_document_limit(tmp_path):
    src = tmp_path / "many.docx"
    _doc(src, " ".join(["СНБ 2.04.02-2000"] * 5))
    dst = tmp_path / "many-out.docx"
    stats = mark_document(src, dst, [{
        "text": "СНБ 2.04.02-2000", "severity": "error", "message": "устарела",
    }])
    assert stats["comments"] == 3

    src2 = tmp_path / "two.docx"
    _doc(src2, "СП 1.01.01-2020. СП 1.01.02-2020.")
    stats2 = mark_document(src2, tmp_path / "two-out.docx", [
        {"text": "СП 1.01.01-2020", "severity": "warn", "message": "a"},
        {"text": "СП 1.01.02-2020", "severity": "warn", "message": "b"},
    ], limit=1)
    assert stats2["comments"] == 1


def test_mark_all_creates_copies_for_each_file(tmp_path):
    for name in ("a", "b"):
        _doc(tmp_path / f"{name}.docx", "СНБ 2.04.02-2000")
    result = {"findings": [{
        "severity": "error", "category": "нормы", "file": "a, b",
        "files": ["a", "b"], "message": "устарела", "norm": "СНБ 2.04.02-2000",
    }]}
    out = tmp_path / "out"
    reports = mark_all(result, tmp_path, out)
    assert len(reports) == 2
    assert all((out / r["file"]).exists() for r in reports)
