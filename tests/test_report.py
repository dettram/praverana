import pytest
from docx import Document
from docx.oxml.ns import qn

from report import MAX_QUOTE_BLOCKS, build_docx, location_unit


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


def test_build_docx_norms_coverage(tmp_path):
    norms = [
        {"code": "СП 5.03.01-2020", "status": "действует", "replacement": "",
         "changed": "—", "source": "реестр", "has_full_text": True},
        {"code": "СП 5.04.01-2021", "status": "нет в реестре", "replacement": "",
         "changed": "", "source": "", "has_full_text": False},
    ]
    doc = Document(build_docx(_result(norms=norms), tmp_path / "report.docx"))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Норм в тексте: 2. Из них с полным текстом в фонде: 1, только по статусу: 1." in text
    assert "Полного текста нет в фонде: СП 5.04.01-2021." in text


def test_build_docx_lists_registry_amendments(tmp_path):
    norms = [{"code": "СП 5.03.01-2020", "status": "действует", "replacement": "",
              "changed": "изм. № 1 (пост. № 33)", "source": "реестр",
              "has_full_text": True}]
    doc = Document(build_docx(_result(norms=norms), tmp_path / "report.docx"))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "В реестре учтены изменения: СП 5.03.01-2020 (изм. № 1 (пост. № 33))" in text
    assert "проверьте актуальность" in text


def test_build_docx_section_order_and_norms_appendix(tmp_path):
    norms = [
        {"code": "СНБ 2.04.02-2000", "status": "не действует",
         "replacement": "СП 2.04.04-2026", "changed": "утратила силу",
         "source": "реестр", "has_full_text": True},
        {"code": "СП 5.03.01-2020", "status": "действует",
         "replacement": "", "changed": "изм. № 1",
         "source": "реестр", "has_full_text": True},
    ]
    doc = Document(build_docx(_result(norms=norms), tmp_path / "report.docx"))
    h1 = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]
    assert h1 == [
        "1 Сводка",
        "2 Замечания",
        "3 Прочитанные документы",
        "4 Разметка документов",
        "5 Ограничения аудита",
        "6 Порядок использования",
        "7 Приложение. Нормы ТНПА в проекте",
    ]
    h2 = [p.text for p in doc.paragraphs if p.style.name == "Heading 2"]
    assert h2 == [
        "2.1 Сводная таблица замечаний",
        "2.2 Ошибки (1)",
        "2.3 Предупреждения (1)",
    ]
    table_text = "\n".join(
        cell.text for table in doc.tables for row in table.rows for cell in row.cells
    )
    assert "Что проверено автоматически" in table_text
    assert "Что не проверялось (требует инженера)" in table_text
    assert "Замена: СП 2.04.04-2026" in table_text
    assert "полный текст (индекс)" in table_text


def test_build_docx_finding_quote_highlight_and_no_empty_quotes(tmp_path):
    findings = [
        {
            "severity": "error",
            "category": "нормы",
            "file": "01-ПЗ",
            "page": None,
            "message": "СНБ 2.04.02-2000 утратила силу",
            "norm": "СНБ 2.04.02-2000",
            "replacement": "СП 2.04.04-2026",
            "action": "Заменить на действующий документ",
            "quote": "Нагрузки приняты по СНБ 2.04.02-2000 и СНиП.",
            "quote_before": "Нагрузки приняты по ",
            "quote_match": "СНБ 2.04.02-2000",
            "quote_after": " и СНиП.",
            "quote_file": "01-ПЗ.docx",
            "quote_page": 1,
        },
        {
            "severity": "info",
            "category": "комплект",
            "file": "07-Смета.xlsx",
            "page": None,
            "message": "формат .xlsx не проверяется",
            "norm": "",
            "action": "Открыть вручную",
            "quote": "",
            "quote_before": "",
            "quote_match": "",
            "quote_after": "",
        },
    ]
    doc = Document(build_docx(_result(findings=findings), tmp_path / "report.docx"))
    quote_paragraphs = [p for p in doc.paragraphs if p.text.startswith("Выдержка")]
    # Только одно замечание имеет выдержку; для второго пустой абзац не создаётся
    assert len(quote_paragraphs) == 1
    qp = quote_paragraphs[0]
    assert "01-ПЗ.docx, фрагм. 1" in qp.text
    assert "«Нагрузки приняты по СНБ 2.04.02-2000 и СНиП.»" in qp.text

    highlighted = [
        r for r in qp.runs if r.text == "СНБ 2.04.02-2000"
    ]
    assert len(highlighted) == 1
    run = highlighted[0]
    assert run.bold is True
    assert run.font.highlight_color is not None
    assert run.font.color.rgb is not None
    assert run.font.name == "Times New Roman"

    # Проверка цепочки замены и неразрывности карточек
    body_paragraphs = [p for p in doc.paragraphs if "→ СП 2.04.04-2026" in p.text]
    assert len(body_paragraphs) == 1
    assert body_paragraphs[0].paragraph_format.keep_with_next is True
    assert body_paragraphs[0].paragraph_format.keep_together is True


def test_build_docx_quote_fallback_from_plain_quote_field(tmp_path):
    findings = [
        {
            "severity": "warn",
            "category": "заглушки",
            "file": "01-ПЗ.docx",
            "page": 2,
            "message": "незаполненный фрагмент «ххх»",
            "norm": "",
            "action": "Заменить",
            "quote": "Ведомость отделки помещений: ХХХ по проекту.",
        },
    ]
    doc = Document(build_docx(_result(findings=findings), tmp_path / "report.docx"))
    quote_paragraphs = [p for p in doc.paragraphs if p.text.startswith("Выдержка")]
    assert len(quote_paragraphs) == 1
    highlighted = [r for r in quote_paragraphs[0].runs if r.font.highlight_color is not None]
    assert len(highlighted) == 1
    assert highlighted[0].text == "ХХХ"
    assert highlighted[0].bold is True


def test_build_docx_limits_quote_blocks(tmp_path):
    total = MAX_QUOTE_BLOCKS + 5
    findings = [
        {
            "severity": "warn",
            "category": "заглушки",
            "file": f"doc-{i}.docx",
            "page": 1,
            "message": f"незаполненный фрагмент «ххх-{i}»",
            "norm": "",
            "action": "Заменить",
            "quote": f"Фрагмент текста документа № {i}: ХХХ-{i}.",
            "quote_before": f"Фрагмент текста документа № {i}: ",
            "quote_match": f"ХХХ-{i}",
            "quote_after": ".",
            "quote_file": f"doc-{i}.docx",
            "quote_page": 1,
        }
        for i in range(1, total + 1)
    ]
    doc = Document(build_docx(_result(findings=findings), tmp_path / "report.docx"))
    quote_paragraphs = [p for p in doc.paragraphs if p.text.startswith("Выдержка")]
    assert len(quote_paragraphs) == MAX_QUOTE_BLOCKS
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert f"показаны для первых {MAX_QUOTE_BLOCKS} замечаний из {total}" in full_text
    # В сводной таблице замечаний присутствуют все total строк (+1 шапка)
    findings_table = next(
        t for t in doc.tables if t.rows[0].cells[0].text == "№" and len(t.columns) == 6
    )
    assert len(findings_table.rows) == total + 1


def test_build_docx_has_toc_and_page_number_fields(tmp_path):
    from docx.oxml.ns import qn

    doc = Document(build_docx(_result(), tmp_path / "report.docx"))

    body = doc.element.body.xml
    assert "TOC \\o" in body
    assert doc.settings.element.find(qn("w:updateFields")) is not None

    footer = doc.sections[0].footer
    fxml = footer._element.xml
    assert " PAGE " in fxml and " NUMPAGES " in fxml
    assert "Стр." in "\n".join(p.text for p in footer.paragraphs)

