import hashlib
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from markdoc import _split_run, collect_marks, mark_all, mark_document

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


def test_mark_document_does_not_modify_source(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    doc.add_paragraph("Применён ГОСТ 27751.")
    doc.save(src)
    before = hashlib.sha256(src.read_bytes()).hexdigest()

    mark_document(src, tmp_path / "out" / "a.docx", [_mark("ГОСТ 27751")])

    assert hashlib.sha256(src.read_bytes()).hexdigest() == before


def test_split_run_splits_text():
    doc = Document()
    paragraph = doc.add_paragraph("abcdef")
    left, right = _split_run(paragraph.runs[0], 3)
    assert left.text == "abc"
    assert right.text == "def"


def test_mark_document_uses_severity_colors(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    doc.add_paragraph("Ошибка: СН 1.02.02 применён.")
    doc.add_paragraph("Предупреждение: СП 5.03.01 в тексте.")
    doc.add_paragraph("Информация: ГОСТ 27751 упомянут.")
    doc.save(src)

    marks = [
        {"text": "СН 1.02.02", "severity": "error", "message": "не действует"},
        {"text": "СП 5.03.01", "severity": "warn", "message": "проверить"},
        {"text": "ГОСТ 27751", "severity": "info", "message": "без года"},
    ]
    mark_document(src, tmp_path / "out" / "a.docx", marks)

    marked = Document(tmp_path / "out" / "a.docx")
    colors = []
    for paragraph in marked.paragraphs[:3]:
        colors += [r.font.highlight_color for r in paragraph.runs if r.font.highlight_color]
    assert colors == [WD_COLOR_INDEX.RED, WD_COLOR_INDEX.YELLOW, WD_COLOR_INDEX.TURQUOISE]


def test_mark_document_marks_table_cells(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "В таблице применён ГОСТ 27751"
    doc.save(src)

    stats = mark_document(src, tmp_path / "out" / "a.docx", [_mark("ГОСТ 27751")])
    assert stats["comments"] == 1

    marked = Document(tmp_path / "out" / "a.docx")
    cell_runs = [r for p in marked.tables[0].cell(0, 0).paragraphs for r in p.runs]
    assert any(r.font.highlight_color for r in cell_runs)


def test_mark_document_caps_three_comments_per_code(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    for _ in range(5):
        doc.add_paragraph("СН 1.02.02 применён в тексте.")
    doc.save(src)

    stats = mark_document(src, tmp_path / "out" / "a.docx", [_mark("СН 1.02.02")])
    assert stats["comments"] == 3


def test_mark_document_respects_document_limit(tmp_path):
    src = tmp_path / "a.docx"
    doc = Document()
    for _ in range(3):
        doc.add_paragraph("СН 1.02.02 и СП 5.03.01 рядом.")
    doc.save(src)

    marks = [_mark("СН 1.02.02"), _mark("СП 5.03.01")]
    stats = mark_document(src, tmp_path / "out" / "a.docx", marks, limit=2)
    assert stats["comments"] == 2
