import pytest
from docx import Document
from docx.oxml.ns import qn

from report import build_docx, location_unit


@pytest.mark.parametrize("file, unit", [
    ("ПЗ.pdf", "стр."),
    ("ПЗ.PDF", "стр."),
    ("ПЗ.docx", "фрагм."),
    ("ПЗ.md", "фрагм."),
    ("ПЗ.txt", "фрагм."),
    ("—", "фрагм."),
    ("", "фрагм."),
])
def test_location_unit(file, unit):
    assert location_unit(file) == unit


def test_report_shows_skipped_and_read_errors(tmp_path):
    from docx import Document

    from report import build_docx

    result = {
        "meta": {"root": "C:/проект", "files_total": 10, "files_scanned": 6, "skipped": 3,
                 "size_mb": 1.2, "duration_s": 0.5, "corpus": "18.11.2026"},
        "summary": {"error": 0, "warn": 0, "info": 0, "score": 10.0},
        "findings": [], "documents": [],
        "errors": ["a.pdf: PermissionError", "b.pdf: EOF"],
    }

    path = build_docx(result, tmp_path / "report.docx")
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    assert "Пропущено без чтения: 3" in text
    assert "Не удалось прочитать файлов: 2" in text
    assert "a.pdf: PermissionError" in text


def _result(**extra) -> dict:
    result = {
        "meta": {"root": "C:/проект", "files_total": 3, "files_scanned": 2,
                 "size_mb": 0.4, "duration_s": 0.3, "corpus": "18.11.2026"},
        "summary": {"error": 1, "warn": 1, "info": 0, "score": 8.0},
        "findings": [
            {"severity": "error", "category": "нормы", "file": "01-ПЗ.docx", "page": None,
             "message": "шифр не действует", "norm": "СН 1.02.02", "action": "заменить"},
            {"severity": "warn", "category": "цитаты", "file": "02-КР.pdf", "page": 5,
             "message": "пункт не найден", "norm": "СП 5.03.01-2020", "action": ""},
        ],
        "documents": [{"file": "01-ПЗ.docx", "pages": 3, "chars": 900}],
    }
    result.update(extra)
    return result


def _style_font(doc, name: str) -> str:
    rfonts = doc.styles[name].element.get_or_add_rPr().find(qn("w:rFonts"))
    return rfonts.get(qn("w:ascii"))


def test_build_docx_a4_margins(tmp_path):
    doc = Document(build_docx(_result(), tmp_path / "report.docx"))
    section = doc.sections[0]
    assert section.left_margin.cm == pytest.approx(2.5, abs=0.01)
    assert section.right_margin.cm == pytest.approx(1.5, abs=0.01)
    assert section.top_margin.cm == pytest.approx(2.0, abs=0.01)
    assert section.bottom_margin.cm == pytest.approx(1.5, abs=0.01)


def test_build_docx_uses_times_new_roman(tmp_path):
    doc = Document(build_docx(_result(), tmp_path / "report.docx"))
    for name in ("Normal", "Heading 1", "Heading 2"):
        assert _style_font(doc, name) == "Times New Roman"

    table_runs = [run for table in doc.tables for row in table.rows
                  for cell in row.cells for p in cell.paragraphs for run in p.runs
                  if run.text]
    assert table_runs
    assert all(run.font.name == "Times New Roman" for run in table_runs)

    bullets = [run for p in doc.paragraphs if p.text.startswith("—")
               for run in p.runs]
    assert bullets
    assert all(run.font.name == "Times New Roman" for run in bullets)


def test_build_docx_tables_repeat_header_row(tmp_path):
    doc = Document(build_docx(_result(), tmp_path / "report.docx"))
    assert doc.tables
    for table in doc.tables:
        tr_pr = table.rows[0]._tr.trPr
        assert tr_pr is not None
        assert tr_pr.find(qn("w:tblHeader")) is not None


def test_build_docx_history_section(tmp_path):
    history = {"previous": {
        "old": {"score": 6.7, "error": 2, "warn": 6, "info": 2},
        "new": {"score": 8.0, "error": 1, "warn": 1, "info": 0},
        "delta": {"score": 1.3, "error": -1, "warn": -5, "info": -2},
        "fixed": [{"category": "нормы", "message": "старое замечание",
                   "norm": "СН 1.02.02"}],
        "fixed_count": 1, "added": [], "added_count": 0,
    }}
    doc = Document(build_docx(_result(history=history), tmp_path / "report.docx"))
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert "1.1 Динамика с предыдущим прогоном" in headings
    text = "\n".join(cell.text for table in doc.tables for row in table.rows
                     for cell in row.cells)
    assert "6,7" in text and "8,0" in text


def test_build_docx_marked_table(tmp_path):
    marked = [{"file": "01-ПЗ.docx", "comments": 2},
              {"file": "02-КР.docx", "error": "ValueError: bad"}]
    doc = Document(build_docx(_result(), tmp_path / "report.docx", marked=marked))
    text = "\n".join(cell.text for table in doc.tables for row in table.rows
                     for cell in row.cells)
    assert "01-ПЗ.docx" in text and "2" in text
    assert "02-КР.docx (ValueError: bad)" in "\n".join(p.text for p in doc.paragraphs)
