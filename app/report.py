"""Отчёт по результатам аудита: DOCX (Times New Roman, А4) и PDF через Word.

  from report import build_docx, to_pdf
  build_docx(result, Path("report.docx"))
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

SEV_LABEL = {"error": "Ошибка", "warn": "Предупреждение", "info": "Информация"}
CAT_ORDER = ("нормы", "цитаты", "комплект", "ПОС/ППР", "заглушки", "подписи")


def location_unit(file: str) -> str:
    """PDF — страница; DOCX, .md и .txt — фрагмент."""
    return "стр." if str(file).lower().endswith(".pdf") else "фрагм."


def _font(style) -> None:
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), "Times New Roman")


def _setup(doc: Document) -> None:
    for style in doc.styles:
        try:
            _font(style)
        except (AttributeError, KeyError):
            continue
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    st.paragraph_format.line_spacing = 1.15
    st.paragraph_format.space_after = Pt(4)
    for name, size in (("Heading 1", 14), ("Heading 2", 12.5)):
        h = doc.styles[name]
        h.font.name = "Times New Roman"
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = None
    sec = doc.sections[0]
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(1.5)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.5)


def _table(doc: Document, headers, rows, widths, size=8.5) -> None:
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    tbl.autofit = False
    tr_pr = tbl.rows[0]._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    for i, text in enumerate(headers):
        cell = tbl.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(str(text))
        run.bold = True
        run.font.size = Pt(size)
        run.font.name = "Times New Roman"
        cell.paragraphs[0].paragraph_format.space_after = Pt(0)
        cell.width = Cm(widths[i])
    for row in rows:
        cells = tbl.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(text))
            run.font.size = Pt(size)
            run.font.name = "Times New Roman"
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
            cells[i].width = Cm(widths[i])
    doc.add_paragraph()


def _bullets(doc: Document, items) -> None:
    """Списки — текстовым тире, а не стилем List Bullet (тот тянет Symbol/Arial)."""
    for it in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-0.5)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run("—\t" + it)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def build_docx(result: dict, out: Path, marked: list[dict] | None = None) -> Path:
    meta = result["meta"]
    summary = result["summary"]
    findings = result["findings"]
    docs = result.get("documents", [])

    doc = Document()
    _setup(doc)

    p = doc.add_paragraph()
    run = p.add_run("ОТЧЁТ ОБ АУДИТЕ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ")
    run.bold = True
    run.font.size = Pt(15)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    run = p.add_run("Черновик. Сформирован автоматически, не является заключением")
    run.italic = True
    run.font.size = Pt(10)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    folder = Path(meta["root"]).name or meta["root"]
    skipped = meta.get("skipped", 0)
    read_errors = result.get("errors") or []
    header_rows = [
        ("Объект (папка)", folder),
        ("Путь", meta["root"]),
        ("Дата отчёта", datetime.now().strftime("%d.%m.%Y %H:%M")),
        ("Файлов в папке / прочитано", f"{meta['files_total']} / {meta['files_scanned']}"),
    ]
    if skipped:
        header_rows.append(("Пропущено без чтения", f"{skipped} (чертежи, модели, архивы)"))
    if read_errors:
        header_rows.append(("Не удалось прочитать", str(len(read_errors))))
    header_rows += [
        ("Объём прочитанного", f"{meta['size_mb']} МБ, {meta['duration_s']} с"),
        ("База ТНПА", f"реестр и индекс фонда: {meta['corpus']}"),
    ]
    _table(doc, ("Параметр", "Значение"), header_rows, widths=(5.0, 11.5), size=10)

    doc.add_heading("1 Сводка", level=1)
    score = summary["score"]
    verdict = ("документы не прочитаны: оценка не выставляется" if meta.get("files_scanned", 0) == 0
               else "документация в целом пригодна к проверке" if score >= 8
               else "требуются исправления до передачи" if score >= 5
               else "существенные дефекты, требуется переработка")
    p = doc.add_paragraph()
    run = p.add_run(f"Оценка: {score} / 10 — {verdict}.")
    run.bold = True
    doc.add_paragraph(
        f"Ошибок: {summary['error']}, предупреждений: {summary['warn']}, "
        f"информационных: {summary['info']}. Оценка учитывает только проверки, "
        "выполненные инструментом (шифры, пункты, комплектность, заглушки); расчёты, "
        "чертежи и решения специалистов не проверялись."
    )

    coverage = (f"Прочитан текст из {meta['files_scanned']} файлов из {meta['files_total']}."
                + (f" Пропущено без чтения: {skipped} (чертежи, модели, архивы,"
                   " неподдерживаемые форматы)." if skipped else "")
                + " Сканы без текстового слоя не проверяются.")
    doc.add_paragraph(coverage)
    if read_errors:
        doc.add_paragraph(
            f"Не удалось прочитать файлов: {len(read_errors)}. Они не проверены; причины ниже."
        )
        _table(doc, ("Файл и причина",), [(str(e)[:180],) for e in read_errors[:10]],
               widths=(16.0,), size=8)

    by_cat: dict[str, list[int]] = {}
    for f in findings:
        row = by_cat.setdefault(f["category"], [0, 0, 0])
        row[{"error": 0, "warn": 1, "info": 2}[f["severity"]]] += 1
    cat_rows = [(cat, *by_cat[cat]) for cat in CAT_ORDER if cat in by_cat]
    cat_rows += [(c, *v) for c, v in by_cat.items() if c not in CAT_ORDER]
    if cat_rows:
        _table(doc, ("Категория", "Ошибки", "Предупреждения", "Инфо"), cat_rows,
               widths=(8.5, 2.6, 3.4, 2.0), size=9)

    prev = (result.get("history") or {}).get("previous")
    if prev:
        doc.add_heading("1.1 Динамика с предыдущим прогоном", level=2)
        d = prev["delta"]
        def signed(x: float) -> str:
            return ("+" if x > 0 else "") + str(x).replace(".", ",")
        def num(x) -> str:
            return str(x).replace(".", ",")
        _table(doc, ("Показатель", "Было", "Стало", "Изменение"), (
            ("Оценка", num(prev["old"]["score"]), num(prev["new"]["score"]), signed(d["score"])),
            ("Ошибки", prev["old"]["error"], prev["new"]["error"], signed(d["error"])),
            ("Предупреждения", prev["old"]["warn"], prev["new"]["warn"], signed(d["warn"])),
            ("Информация", prev["old"]["info"], prev["new"]["info"], signed(d["info"])),
        ), widths=(6.0, 3.4, 3.4, 3.6), size=9)
        if prev["fixed"]:
            doc.add_paragraph(f"Исправлено замечаний: {prev.get('fixed_count', len(prev['fixed']))}")
            _table(doc, ("Уровень", "Категория", "Замечание", "Норма"),
                   [("исправлено", f["category"], f["message"][:120], f["norm"] or "—")
                    for f in prev["fixed"][:12]],
                   widths=(2.4, 2.6, 8.6, 3.4), size=8)
        if prev.get("scope_changed"):
            doc.add_paragraph(
                f"Состав выборки изменился: было {prev['files_old']} документов, стало "
                f"{prev['files_new']}. Сравнение по числу замечаний в этом случае условное."
            )
        if prev["added"]:
            doc.add_paragraph(f"Появилось новых замечаний: {prev.get('added_count', len(prev['added']))}")
            _table(doc, ("Уровень", "Категория", "Замечание", "Норма"),
                   [(f["severity"], f["category"], f["message"][:120], f["norm"] or "—")
                    for f in prev["added"][:12]],
                   widths=(2.4, 2.6, 8.6, 3.4), size=8)

    doc.add_heading("2 Замечания", level=1)
    if not findings:
        doc.add_paragraph("Замечаний не выявлено выполненными проверками.")
    else:
        rows = []
        for i, f in enumerate(findings, 1):
            where = f["file"] if f["file"] != "—" else "комплект проекта"
            if f.get("page"):
                unit = location_unit(f.get("file", ""))
                where += f", {unit} {f['page']}"
            rows.append((i, SEV_LABEL[f["severity"]], f["category"], where,
                         f["message"], f["norm"] or "—", f["action"] or "—"))
        _table(doc, ("№", "Уровень", "Категория", "Где", "Замечание", "Норма", "Действие"),
               rows, widths=(0.8, 2.5, 2.1, 3.6, 3.5, 2.0, 2.3), size=8)

    doc.add_heading("3 Прочитанные документы", level=1)
    if docs:
        rows = [(i, d["file"], d["pages"], d["chars"]) for i, d in enumerate(docs[:40], 1)]
        _table(doc, ("№", "Файл", "Фрагментов", "Знаков"), rows,
               widths=(0.9, 11.6, 2.2, 2.0), size=8)
        if len(docs) > 40:
            doc.add_paragraph(f"…и ещё {len(docs) - 40} файлов (см. панель аудита).")
    else:
        doc.add_paragraph("Текстовые документы не прочитаны.")

    doc.add_heading("4 Разметка документов", level=1)
    if marked:
        placed = [m for m in marked if m.get("comments")]
        failed = [m for m in marked if m.get("error")]
        if placed:
            doc.add_paragraph(
                "Подготовлены копии документов с комментариями Word и подсветкой найденных мест: "
                "ошибки — красным, предупреждения — жёлтым, информация — бирюзовым. "
                "Размеченные копии выдаются архивом «Размеченные-документы.zip»."
            )
            _table(doc, ("Файл", "Комментариев"),
                   [(m["file"], m["comments"]) for m in placed],
                   widths=(13.5, 3.0), size=9)
        if failed:
            doc.add_paragraph("Не удалось разметить: " + "; ".join(
                f"{m['file']} ({m['error']})" for m in failed))
        if not placed and not failed:
            doc.add_paragraph("В проекте нет DOCX-документов, к которым привязаны замечания.")
    else:
        doc.add_paragraph("Разметка не запрашивалась.")

    doc.add_heading("5 Ограничения аудита", level=1)
    _bullets(doc, (
        "Проверялись только текстовые документы (.docx, .pdf) и только извлекаемый текст: "
        "сканы без OCR, чертежи DWG, модели RVT, таблицы XLSX и DOC не анализировались.",
        f"Статусы норм взяты из реестра: {meta['corpus']}; полный текст есть в фонде для 46 из 141 "
        "документа, остальные проверены только по статусу.",
        "Пункты норм проверялись по индексу фонда: «пункт не найден» означает, что его нет в "
        "проиндексированных текстах, а не что он отменён.",
        "Расчёты, армирование, нагрузки, решения по пожарной безопасности и сметы не проверялись.",
        "Проверка комплектности выполняется по именам файлов и может давать ложные срабатывания "
        "при нестандартных именах.",
        "Разметка ставится на первые вхождения (до трёх на один шифр) и только в DOCX; "
        "в PDF комментарии не добавляются — для них остаётся таблица замечаний.",
    ))

    doc.add_heading("6 Порядок использования", level=1)
    doc.add_paragraph(
        "Отчёт является черновиком для инженера: каждое замечание нужно подтвердить по документу, "
        "а решение — принять с учётом стадии проектирования. Отчёт не заменяет нормоконтроль и "
        "заключение экспертизы."
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return out


PS_SCRIPT = r"""
$ErrorActionPreference = "Stop"
$cfg = Get-Content -LiteralPath $args[0] -Raw -Encoding UTF8 | ConvertFrom-Json
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
foreach ($p in $cfg) {
    $doc = $w.Documents.Open($p.docx, $false, $false)
    try {
        $doc.Save()
        $doc.ExportAsFixedFormat($p.pdf, 17)
    } finally {
        $doc.Close($false)
    }
}
$w.Quit()
"""


def to_pdf(docx_path: Path, pdf_path: Path) -> Path:
    """Экспорт DOCX → PDF через Word (Windows). Возвращает путь к PDF."""
    payload = [{"docx": str(docx_path), "pdf": str(pdf_path)}]
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "cfg.json"
        cfg.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        ps = Path(td) / "export.ps1"
        ps.write_text(PS_SCRIPT, encoding="utf-8")
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps), str(cfg)],
            check=True, capture_output=True, timeout=180,
        )
    if not pdf_path.exists():
        raise RuntimeError("PDF не создан")
    return pdf_path
