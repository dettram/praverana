"""Отчёт по результатам аудита: DOCX (Times New Roman, А4) и PDF через Word.

  from report import build_docx, to_pdf
  build_docx(result, Path("report.docx"))
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SEV_LABEL = {"error": "Ошибка", "warn": "Предупреждение", "info": "Информация"}
SEV_SECTION = {"error": "Ошибки", "warn": "Предупреждения", "info": "Информация"}
SEV_COLOR = {
    "error": RGBColor(0x9B, 0x1C, 0x1C),
    "warn": RGBColor(0x7A, 0x4E, 0x06),
    "info": RGBColor(0x15, 0x43, 0x60),
}
SEV_BORDER_HEX = {"error": "C8102E", "warn": "A97C22", "info": "2B5B84"}
QUOTE_HIGHLIGHT = {
    "error": WD_COLOR_INDEX.YELLOW,
    "warn": WD_COLOR_INDEX.YELLOW,
    "info": WD_COLOR_INDEX.TURQUOISE,
}
CAT_ORDER = ("нормы", "цитаты", "комплект", "ПОС/ППР", "заглушки", "подписи")
MAX_QUOTE_BLOCKS = 25

SCOPE_ROWS = (
    (
        "Шифры ТНПА (СН, СП, ТКП, СТБ, ГОСТ, СНиП) по реестру действующих норм и цепочкам замены",
        "Инженерные расчёты, нагрузки, армирование, гидравлика, теплотехника и сметная стоимость",
    ),
    (
        "Ссылки на пункты, таблицы и приложения по проиндексированным полным текстам фонда",
        "Графическая часть (чертежи DWG, модели RVT/IFC), таблицы XLSX/DOC и сканы без текстового слоя (OCR)",
    ),
    (
        "Комплектность основных разделов по составу файлов и обязательные разделы ПОС/ППР (СН 1.03.04-2020)",
        "Применимость конкретной нормы и пункта к проектным решениям и стадии проектирования",
    ),
    (
        "Незаполненные заглушки («ХХХ», «___», «по проекту») и пустые графы в листах подписей",
        "Подлинность подписей, печатей и соответствие бумажному оригиналу",
    ),
)


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
        h.paragraph_format.keep_with_next = True
        h.paragraph_format.space_before = Pt(10 if name == "Heading 1" else 7)
        h.paragraph_format.space_after = Pt(4)
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(1.5)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.5)


def _add_run(
    p,
    text: str,
    *,
    size: float = 11,
    bold: bool = False,
    italic: bool = False,
    color: RGBColor | None = None,
    highlight=None,
):
    run = p.add_run(str(text))
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    if bold:
        run.bold = True
    if italic:
        run.italic = True
    if color is not None:
        run.font.color.rgb = color
    if highlight is not None:
        run.font.highlight_color = highlight
    return run


def _set_cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))


def _table(doc: Document, headers, rows, widths, size=8.5) -> None:
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    tbl.autofit = False
    tr_pr = tbl.rows[0]._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))
    _prevent_row_split(tbl.rows[0])
    for i, text in enumerate(headers):
        cell = tbl.rows[0].cells[i]
        cell.text = ""
        _set_cell_shading(cell, "EFECE6")
        _add_run(cell.paragraphs[0], str(text), size=size, bold=True)
        cell.paragraphs[0].paragraph_format.space_after = Pt(0)
        cell.width = Cm(widths[i])
    for row in rows:
        tr = tbl.add_row()
        _prevent_row_split(tr)
        cells = tr.cells
        for i, text in enumerate(row):
            cells[i].text = ""
            _add_run(cells[i].paragraphs[0], str(text), size=size)
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
        _add_run(p, "—\t" + it, size=12)


def _finding_where(f: dict) -> str:
    where = f["file"] if f.get("file") and f["file"] != "—" else "комплект проекта"
    if f.get("page"):
        unit = location_unit(f.get("file", ""))
        where += f", {unit} {f['page']}"
    return where


def _quote_where(f: dict) -> str:
    qfile = f.get("quote_file") or f.get("file") or ""
    if not qfile or qfile == "—":
        return ""
    qpage = f.get("quote_page") if f.get("quote_page") is not None else f.get("page")
    if qpage:
        return f"{qfile}, {location_unit(qfile)} {qpage}"
    return str(qfile)


def _finding_norm(f: dict) -> str:
    norm = f.get("norm") or "—"
    if f.get("replacement"):
        norm += " → " + f["replacement"]
    return norm


def extract_quote_parts(f: dict) -> tuple[str, str, str] | None:
    """Возвращает (before, match, after) для выдержки или None, если выдержки нет."""
    match = str(f.get("quote_match") or "").strip()
    if match:
        before = str(f.get("quote_before") or "")
        after = str(f.get("quote_after") or "")
        return before, match, after

    raw_quote = str(f.get("quote") or "").strip()
    if not raw_quote:
        return None

    needles: list[str] = []
    norm_full = str(f.get("norm") or "").strip()
    if norm_full:
        needles.append(norm_full)
        first_norm = norm_full.split(",")[0].strip()
        if first_norm and first_norm not in needles:
            needles.append(first_norm)
    msg = str(f.get("message") or "")
    if "«" in msg and "»" in msg:
        in_quotes = msg.split("«", 1)[1].split("»", 1)[0].strip()
        if in_quotes:
            needles.append(in_quotes)

    for needle in needles:
        m = re.search(re.escape(needle), raw_quote, re.IGNORECASE)
        if m:
            return raw_quote[:m.start()], raw_quote[m.start():m.end()], raw_quote[m.end():]
    return "", raw_quote, ""


def _style_quote_paragraph(p, border_hex: str) -> None:
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.right_indent = Cm(0.3)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_together = True

    p_pr = p._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "12")
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), border_hex)
    p_bdr.append(left)
    p_pr.append(p_bdr)

    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F7F6F2")
    p_pr.append(shd)


def _render_finding_block(doc: Document, idx: int, f: dict) -> None:
    """Рендерит неразрывный блок замечания с метаданными и (при наличии) выдержкой."""
    sev = f["severity"]
    where = _finding_where(f)
    qparts = extract_quote_parts(f)

    p_head = doc.add_paragraph()
    p_head.paragraph_format.space_before = Pt(6)
    p_head.paragraph_format.space_after = Pt(1)
    p_head.paragraph_format.keep_with_next = True
    p_head.paragraph_format.keep_together = True
    _add_run(
        p_head,
        f"№ {idx}  [{SEV_LABEL.get(sev, sev)}]",
        size=10.5,
        bold=True,
        color=SEV_COLOR.get(sev),
    )
    _add_run(
        p_head,
        f"  Категория: {f['category']}  |  Где: {where}",
        size=10,
        bold=True,
    )

    p_body = doc.add_paragraph()
    p_body.paragraph_format.left_indent = Cm(0.4)
    p_body.paragraph_format.space_before = Pt(0)
    p_body.paragraph_format.space_after = Pt(2 if qparts else 5)
    p_body.paragraph_format.keep_with_next = bool(qparts)
    p_body.paragraph_format.keep_together = True
    _add_run(p_body, "Замечание: ", size=10, bold=True)
    _add_run(p_body, f.get("message", ""), size=10)
    if f.get("norm") or f.get("replacement"):
        _add_run(p_body, "  |  Норма: ", size=10, bold=True)
        _add_run(p_body, f.get("norm") or "—", size=10)
        if f.get("replacement"):
            _add_run(p_body, f" → {f['replacement']}", size=10, bold=True)
    if f.get("action"):
        _add_run(p_body, "  |  Действие: ", size=10, bold=True)
        _add_run(p_body, f["action"], size=10)

    if qparts is not None:
        before, match, after = qparts
        p_quote = doc.add_paragraph()
        _style_quote_paragraph(p_quote, SEV_BORDER_HEX.get(sev, "8A5F14"))
        qwhere = _quote_where(f)
        label = f"Выдержка ({qwhere}): " if qwhere else "Выдержка: "
        _add_run(
            p_quote,
            label,
            size=9.5,
            italic=True,
            color=RGBColor(0x55, 0x55, 0x55),
        )
        _add_run(p_quote, "«" + before, size=10)
        if match:
            _add_run(
                p_quote,
                match,
                size=10,
                bold=True,
                color=SEV_COLOR.get(sev),
                highlight=QUOTE_HIGHLIGHT.get(sev, WD_COLOR_INDEX.YELLOW),
            )
        _add_run(p_quote, after + "»", size=10)


def build_docx(result: dict, out: Path, marked: list[dict] | None = None) -> Path:
    meta = result["meta"]
    summary = result["summary"]
    findings = result["findings"]
    docs = result.get("documents", [])

    doc = Document()
    _setup(doc)

    p = doc.add_paragraph()
    _add_run(p, "ОТЧЁТ ОБ АУДИТЕ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ", size=15, bold=True)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    _add_run(
        p,
        "Черновик. Сформирован автоматически, не является заключением",
        size=10,
        italic=True,
    )
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    score = summary["score"]
    verdict = (
        "документы не прочитаны: оценка не выставляется"
        if meta.get("files_scanned", 0) == 0
        else "документация в целом пригодна к проверке"
        if score >= 8
        else "требуются исправления до передачи"
        if score >= 5
        else "существенные дефекты, требуется переработка"
    )

    folder = Path(meta["root"]).name or meta["root"]
    skipped = meta.get("skipped", 0)
    read_errors = result.get("errors") or []
    header_rows = [
        ("Объект (папка)", folder),
        ("Путь", meta["root"]),
        ("Дата отчёта", datetime.now().strftime("%d.%m.%Y %H:%M")),
        ("Оценка и вердикт", f"{score} / 10 — {verdict}"),
        (
            "Замечаний (ошибки / предупр. / инфо)",
            f"{len(findings)} ({summary['error']} / {summary['warn']} / {summary['info']})",
        ),
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
    p = doc.add_paragraph()
    _add_run(p, f"Оценка: {score} / 10 — {verdict}.", size=12, bold=True)
    doc.add_paragraph(
        f"Ошибок: {summary['error']}, предупреждений: {summary['warn']}, "
        f"информационных: {summary['info']}. Оценка учитывает только проверки, "
        "выполненные инструментом (шифры, пункты, комплектность, заглушки); расчёты, "
        "чертежи и решения специалистов не проверялись."
    )

    norms = result.get("norms") or []
    if norms:
        full = sum(1 for n in norms if n.get("has_full_text"))
        doc.add_paragraph(
            f"Норм в тексте: {len(norms)}. Из них с полным текстом в фонде: {full}, "
            f"только по статусу: {len(norms) - full}."
        )
        without = [n["code"] for n in norms if not n.get("has_full_text")]
        if without:
            shown = ", ".join(without[:20]) + ("…" if len(without) > 20 else "")
            doc.add_paragraph(f"Полного текста нет в фонде: {shown}.")
        amended = [n for n in norms if n.get("changed")]
        if amended:
            shown = "; ".join(f"{n['code']} ({n['changed']})" for n in amended[:10])
            if len(amended) > 10:
                shown += "…"
            doc.add_paragraph(
                f"В реестре учтены изменения: {shown} — проверьте актуальность "
                "конкретных пунктов и таблиц."
            )

    coverage = (
        f"Прочитан текст из {meta['files_scanned']} файлов из {meta['files_total']}."
        + (
            f" Пропущено без чтения: {skipped} (чертежи, модели, архивы,"
            " неподдерживаемые форматы)."
            if skipped
            else ""
        )
        + " Сканы без текстового слоя не проверяются."
    )
    doc.add_paragraph(coverage)
    if read_errors:
        doc.add_paragraph(
            f"Не удалось прочитать файлов: {len(read_errors)}. Они не проверены; причины ниже."
        )
        _table(
            doc,
            ("Файл и причина",),
            [(str(e)[:180],) for e in read_errors[:10]],
            widths=(16.0,),
            size=8,
        )

    by_cat: dict[str, list[int]] = {}
    for f in findings:
        row = by_cat.setdefault(f["category"], [0, 0, 0])
        row[{"error": 0, "warn": 1, "info": 2}[f["severity"]]] += 1
    cat_rows = [(cat, *by_cat[cat]) for cat in CAT_ORDER if cat in by_cat]
    cat_rows += [(c, *v) for c, v in by_cat.items() if c not in CAT_ORDER]
    if cat_rows:
        _table(
            doc,
            ("Категория", "Ошибки", "Предупреждения", "Инфо"),
            cat_rows,
            widths=(8.5, 2.6, 3.4, 2.0),
            size=9,
        )

    p_scope = doc.add_paragraph()
    p_scope.paragraph_format.keep_with_next = True
    _add_run(
        p_scope,
        "Границы автоматической проверки (что проверено и что не проверялось):",
        size=11,
        bold=True,
    )
    _table(
        doc,
        ("Что проверено автоматически", "Что не проверялось (требует инженера)"),
        SCOPE_ROWS,
        widths=(8.25, 8.25),
        size=8.5,
    )

    prev = (result.get("history") or {}).get("previous")
    if prev:
        doc.add_heading("1.1 Динамика с предыдущим прогоном", level=2)
        d = prev["delta"]

        def signed(x: float) -> str:
            return ("+" if x > 0 else "") + str(x).replace(".", ",")

        def num(x) -> str:
            return str(x).replace(".", ",")

        _table(
            doc,
            ("Показатель", "Было", "Стало", "Изменение"),
            (
                ("Оценка", num(prev["old"]["score"]), num(prev["new"]["score"]), signed(d["score"])),
                ("Ошибки", prev["old"]["error"], prev["new"]["error"], signed(d["error"])),
                ("Предупреждения", prev["old"]["warn"], prev["new"]["warn"], signed(d["warn"])),
                ("Информация", prev["old"]["info"], prev["new"]["info"], signed(d["info"])),
            ),
            widths=(6.0, 3.4, 3.4, 3.6),
            size=9,
        )
        if prev["fixed"]:
            doc.add_paragraph(
                f"Исправлено замечаний: {prev.get('fixed_count', len(prev['fixed']))}"
            )
            _table(
                doc,
                ("Уровень", "Категория", "Замечание", "Норма"),
                [
                    ("исправлено", f["category"], f["message"][:120], f["norm"] or "—")
                    for f in prev["fixed"][:12]
                ],
                widths=(2.4, 2.6, 8.6, 3.4),
                size=8,
            )
        if prev.get("scope_changed"):
            doc.add_paragraph(
                f"Состав выборки изменился: было {prev['files_old']} документов, стало "
                f"{prev['files_new']}. Сравнение по числу замечаний в этом случае условное."
            )
        if prev["added"]:
            doc.add_paragraph(
                f"Появилось новых замечаний: {prev.get('added_count', len(prev['added']))}"
            )
            _table(
                doc,
                ("Уровень", "Категория", "Замечание", "Норма"),
                [
                    (f["severity"], f["category"], f["message"][:120], f["norm"] or "—")
                    for f in prev["added"][:12]
                ],
                widths=(2.4, 2.6, 8.6, 3.4),
                size=8,
            )

    doc.add_heading("2 Замечания", level=1)
    if not findings:
        doc.add_paragraph("Замечаний не выявлено выполненными проверками.")
    else:
        indexed = list(enumerate(findings, 1))
        rendered_blocks = 0
        sub_idx = 0
        for sev in ("error", "warn", "info"):
            group = [(i, f) for i, f in indexed if f["severity"] == sev]
            if not group:
                continue
            sub_idx += 1
            doc.add_heading(f"2.{sub_idx} {SEV_SECTION[sev]} ({len(group)})", level=2)
            for i, f in group:
                if rendered_blocks >= MAX_QUOTE_BLOCKS:
                    break
                _render_finding_block(doc, i, f)
                rendered_blocks += 1

        if len(findings) > MAX_QUOTE_BLOCKS:
            p_lim = doc.add_paragraph()
            _add_run(
                p_lim,
                f"Детальные карточки с выдержками показаны для первых {MAX_QUOTE_BLOCKS} "
                f"замечаний из {len(findings)}; остальные {len(findings) - MAX_QUOTE_BLOCKS} "
                "приведены в сводной таблице ниже.",
                size=10,
                italic=True,
            )

        sub_idx += 1
        doc.add_heading(f"2.{sub_idx} Сводная таблица замечаний", level=2)
        rows = []
        for i, f in indexed:
            rows.append((
                i,
                SEV_LABEL[f["severity"]],
                f["category"],
                _finding_where(f),
                f["message"],
                _finding_norm(f),
                f.get("action") or "—",
            ))
        _table(
            doc,
            ("№", "Уровень", "Категория", "Где", "Замечание", "Норма", "Действие"),
            rows,
            widths=(0.8, 2.5, 2.1, 3.6, 3.5, 2.0, 2.3),
            size=8,
        )

    doc.add_heading("3 Прочитанные документы", level=1)
    if docs:
        rows = [(i, d["file"], d["pages"], d["chars"]) for i, d in enumerate(docs[:40], 1)]
        _table(
            doc,
            ("№", "Файл", "Фрагментов", "Знаков"),
            rows,
            widths=(0.9, 11.6, 2.2, 2.0),
            size=8,
        )
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
            _table(
                doc,
                ("Файл", "Комментариев"),
                [(m["file"], m["comments"]) for m in placed],
                widths=(13.5, 3.0),
                size=9,
            )
        if failed:
            doc.add_paragraph(
                "Не удалось разметить: "
                + "; ".join(f"{m['file']} ({m['error']})" for m in failed)
            )
        if not placed and not failed:
            doc.add_paragraph("В проекте нет DOCX-документов, к которым привязаны замечания.")
    else:
        doc.add_paragraph("Разметка не запрашивалась.")

    doc.add_heading("5 Ограничения аудита", level=1)
    _bullets(
        doc,
        (
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
            "в PDF комментарии не добавляются — для них остаётся таблица замечаний и выдержки в отчёте.",
        ),
    )

    doc.add_heading("6 Порядок использования", level=1)
    doc.add_paragraph(
        "Отчёт является черновиком для инженера: каждое замечание нужно подтвердить по документу, "
        "а решение — принять с учётом стадии проектирования. Отчёт не заменяет нормоконтроль и "
        "заключение экспертизы."
    )

    doc.add_heading("7 Приложение. Нормы ТНПА в проекте", level=1)
    if norms:
        norm_rows = []
        for n in norms[:60]:
            chain_parts = []
            if n.get("replacement"):
                chain_parts.append(f"Замена: {n['replacement']}")
            if n.get("changed") and n["changed"] != "—":
                chain_parts.append(f"Изм.: {n['changed']}")
            chain = "; ".join(chain_parts) if chain_parts else "—"
            coverage_label = (
                "полный текст (индекс)" if n.get("has_full_text") else "только статус (реестр)"
            )
            norm_rows.append((
                n.get("code", "—"),
                n.get("status", "—"),
                chain,
                coverage_label,
            ))
        _table(
            doc,
            ("Шифр ТНПА", "Статус в реестре", "Замена / изменения", "Проверка пунктов"),
            norm_rows,
            widths=(4.0, 3.8, 5.2, 3.5),
            size=8.5,
        )
        if len(norms) > 60:
            doc.add_paragraph(f"…и ещё {len(norms) - 60} норм (см. JSON-отчёт прогона).")
    else:
        doc.add_paragraph("Ссылки на шифры ТНПА в прочитанных документах не обнаружены.")

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return out


PS_SCRIPT = r"""
$ErrorActionPreference = "Stop"
$cfg = Get-Content -LiteralPath $args[0] -Raw -Encoding UTF8 | ConvertFrom-Json
$w = New-Object -ComObject Word.Application
try {
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
} finally {
    # Word не должен оставаться в фоне, даже если Open или Export упали
    $w.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($w)
}
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
            check=True,
            capture_output=True,
            timeout=180,
        )
    if not pdf_path.exists():
        raise RuntimeError("PDF не создан")
    return pdf_path
