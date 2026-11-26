import pytest
from docx import Document

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


def _result():
    return {
        "meta": {
            "root": r"C:\demo-project", "files_total": 3, "files_scanned": 2,
            "size_mb": 0.1, "duration_s": 0.1, "corpus": "18.11.2026",
        },
        "summary": {"score": 6.8, "error": 1, "warn": 1, "info": 0},
        "findings": [
            {
                "severity": "error", "category": "нормы", "file": "ПЗ.docx", "page": 1,
                "message": "устаревший шифр", "norm": "СНБ 2.04.02-2000",
                "action": "заменить",
            },
            {
                "severity": "warn", "category": "заглушки", "file": "ПЗ.docx", "page": 2,
                "message": "незаполненный фрагмент «ххх»", "norm": "",
                "action": "заполнить",
            },
        ],
        "documents": [
            {"file": "ПЗ.docx", "pages": 2, "chars": 100},
            {"file": "АР.docx", "pages": 1, "chars": 50},
        ],
    }


def _text(doc):
    chunks = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                chunks.extend(p.text for p in cell.paragraphs)
    return "\n".join(chunks)


def _run_names(doc):
    names = set()
    paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    paragraphs.extend(doc.sections[0].header.paragraphs)
    paragraphs.extend(doc.sections[0].footer.paragraphs)
    for paragraph in paragraphs:
        for run in paragraph.runs:
            if run.font.name:
                names.add(run.font.name)
    return names


def test_build_docx_has_register_structure(tmp_path):
    out = build_docx(_result(), tmp_path / "report.docx")
    doc = Document(str(out))
    text = _text(doc)

    assert "Отчёт об автоматизированной проверке проекта" in text
    assert "demo-project" in text
    assert "1 Указатель замечаний" in text
    assert "2 Карточки замечаний" in text
    assert "3 Как проверить замечание" in text
    assert "4 Прочитанные документы" in text
    assert "5 Решение" not in text
    assert "З-01" in text
    assert "З-02" in text
    assert "Ошибка" in text
    assert "Предупреждение" in text
    assert "Тик слева" in text

    assert len(doc.inline_shapes) >= 1
    assert len(doc.tables) >= 6
    assert doc.styles["Normal"].font.name == "Times New Roman"
    assert doc.styles["Heading 1"].font.name == "Times New Roman"
    assert _run_names(doc) == {"Times New Roman"}


def test_page_is_a4_and_has_running_heads(tmp_path):
    doc = Document(str(build_docx(_result(), tmp_path / "report.docx")))
    section = doc.sections[0]

    assert round(section.page_width.cm, 1) == 21.0
    assert round(section.page_height.cm, 1) == 29.7
    assert round(section.left_margin.cm, 1) == 2.5
    assert round(section.right_margin.cm, 1) == 1.5
    assert section.different_first_page_header_footer is True

    assert "Праверана.by" in section.header.paragraphs[0].text
    assert "реестр проверки" in section.header.paragraphs[0].text
    assert "стр." in section.footer.paragraphs[0].text

    assert section.first_page_header.paragraphs[0].text == ""
    assert section.first_page_footer.paragraphs[0].text == ""


def test_empty_findings_are_explained(tmp_path):
    result = _result()
    result["findings"] = []
    result["summary"] = {"score": 10.0, "error": 0, "warn": 0, "info": 0}
    text = _text(Document(str(build_docx(result, tmp_path / "empty.docx"))))
    assert "Замечаний не выявлено выполненными проверками." in text
    assert "Замечаний нет: карточки не сформированы." in text


def test_no_scanned_docs_do_not_get_score(tmp_path):
    result = _result()
    result["meta"]["files_scanned"] = 0
    result["documents"] = []
    result["findings"] = [{
        "severity": "info", "category": "комплект", "file": "—", "page": None,
        "message": "текстовые документы не прочитаны: нет DOCX/PDF с текстовым слоем",
        "norm": "", "action": "Проверить формат файлов",
    }]
    result["summary"] = {"score": 0.0, "error": 0, "warn": 0, "info": 1}
    text = _text(Document(str(build_docx(result, tmp_path / "no-text.docx"))))
    assert "Документы не прочитаны" in text
    assert "Оценка не выставляется" in text
    assert "0 из 10" not in text


def test_report_coverage_distinguishes_limit(tmp_path):
    result = _result()
    result["meta"]["files_total"] = 4
    result["meta"]["files_scanned"] = 1
    result["meta"]["truncated"] = 2
    result["documents"] = [{"file": "ПЗ.docx", "pages": 1, "chars": 100}]
    text = _text(Document(str(build_docx(result, tmp_path / "limited.docx"))))
    assert "из них 2 — предел" in text
    assert "не вошли в лимит (2)" in text


def test_marking_section_lists_marked_files(tmp_path):
    marked = [{"file": "ПЗ.docx", "comments": 3}]
    text = _text(Document(str(build_docx(_result(), tmp_path / "marked.docx", marked))))
    assert "Разметка документов" in text
    assert "praverana-marked.zip" in text
    assert "ПЗ.docx" in text
