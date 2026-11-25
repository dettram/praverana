import pytest

from report import location_unit


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
