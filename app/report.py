"""Отчёт по результатам аудита: DOCX (A4, реестр проверки) и PDF через Word.

  from report import build_docx, to_pdf
  build_docx(result, Path("report.docx"))

Вёрстка: один Times New Roman, белая бумага, цвет только у суждения
(уровень замечания и вердикт). Обложка — карточка объекта, вторая страница —
указатель, дальше карточки с адресом, нормой и действием.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

INK = "15181A"
MUTED = "5D666B"
LINE = "E4E0D6"
LINE_STRONG = "C9C9C4"
RED = "C8102E"
GOLD_TEXT = "8A5F14"
GREEN = "23694A"
SLATE = "3A4A5A"

SEV_LABEL = {"error": "Ошибка", "warn": "Предупреждение", "info": "Примечание"}
SEV_COLOR = {"error": RED, "warn": GOLD_TEXT, "info": SLATE}
SEV_TICK = {"error": 24, "warn": 12, "info": 6}  # восьмые доли пункта: 3 / 1,5 / 0,75 pt

CAT_ORDER = ("нормы", "цитаты", "комплект", "ПОС/ППР", "заглушки", "подписи")
CAT_CHECK = {
    "нормы": "ссылки на нормы",
    "цитаты": "цитаты и пункты",
    "комплект": "комплектность и форматы",
    "ПОС/ППР": "ПОС и ППР",
    "заглушки": "заглушки и шаблоны",
    "подписи": "подписи и согласования",
}

STAMP = Path(__file__).resolve().parent / "ui" / "assets" / "logo" / "png" / "mark.png"
OCCURS = re.compile(r"\s*\(встречается\s+(\d+)\s+раз(?:а)?\)")


# --------------------------------------------------------------------------- #
# Примитивы
# --------------------------------------------------------------------------- #
def location_unit(file: str) -> str:
    """PDF — страница; DOCX, .md и .txt — фрагмент."""
    return "стр." if str(file).lower().endswith(".pdf") else "фрагм."


def _rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value.lstrip("#"))


def _font(style, name: str = "Times New Roman") -> None:
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)


def _run_font(run, name: str = "Times New Roman") -> None:
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)


def _run(p, text: str, size: float = 10, color: str = INK,
         bold: bool = False, italic: bool = False):
    run = p.add_run(text)
    _run_font(run)
    run.font.size = Pt(size)
    run.font.color.rgb = _rgb(color)
    run.bold = bold
    run.italic = italic
    return run


def _fmt(p, before: float = 0, after: float = 0, line: float | None = None,
         keep: bool = False, align=None) -> None:
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if line is not None:
        pf.line_spacing = Pt(line)
    if keep:
        pf.keep_with_next = True
    if align is not None:
        p.alignment = align


def _p_border(p, edge: str, color: str, size: int = 6) -> None:
    ppr = p._p.get_or_add_pPr()
    borders = ppr.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        ppr.append(borders)
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), "4")
    el.set(qn("w:color"), color)
    borders.append(el)


def _cell_border(cell, edge: str, color: str, size: int = 4,
                 val: str = "single") -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    borders = tcpr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcpr.append(borders)
    el = borders.find(qn(f"w:{edge}"))
    if el is None:
        el = OxmlElement(f"w:{edge}")
        borders.append(el)
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), color)


def _table_borders(table, spec: dict[str, tuple[str, int, str] | None]) -> None:
    tblpr = table._tbl.tblPr
    old = tblpr.find(qn("w:tblBorders"))
    if old is not None:
        tblpr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        rule = spec.get(edge)
        if rule is None:
            el.set(qn("w:val"), "nil")
        else:
            val, size, color = rule
            el.set(qn("w:val"), val)
            el.set(qn("w:sz"), str(size))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), color)
        borders.append(el)
    tblpr.append(borders)


def _no_borders(table) -> None:
    _table_borders(table, {})


def _fixed(table, widths, pad_x: float = 0.15, pad_y: float = 0.08) -> None:
    """Фиксированная сетка: ширины колонок и поля ячеек в сантиметрах."""
    table.autofit = False
    for i, width in enumerate(widths):
        table.columns[i].width = Cm(width)
        for cell in table.columns[i].cells:
            cell.width = Cm(width)
    tblpr = table._tbl.tblPr
    old = tblpr.find(qn("w:tblCellMar"))
    if old is not None:
        tblpr.remove(old)
    mar = OxmlElement("w:tblCellMar")
    for edge, value in (("top", pad_y), ("left", pad_x),
                        ("bottom", pad_y), ("right", pad_x)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(max(0, int(value * 567))))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.append(mar)


def _gap(doc: Document, size: float = 6) -> None:
    p = doc.add_paragraph()
    _fmt(p, 0, 0, size)


def _field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    _run_font(run)
    run.font.size = Pt(8)
    run.font.color.rgb = _rgb(MUTED)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


def _heading(doc: Document, text: str, level: int = 1, new_page: bool = False):
    p = doc.add_paragraph(style=f"Heading {level}")
    _fmt(p, 14 if level == 1 else 10, 6 if level == 1 else 3,
         keep=True)
    if new_page:
        p.paragraph_format.page_break_before = True
    run = p.add_run(text)
    _run_font(run)
    run.font.size = Pt(14 if level == 1 else 11.5)
    run.bold = True
    run.font.color.rgb = _rgb(INK)
    if level == 1:
        _p_border(p, "bottom", LINE_STRONG, 4)
    return p


def _label_value(p, label: str, value: str, size: float = 9.5,
                 color: str = INK) -> None:
    _run(p, label.upper() + " · ", 7, MUTED, bold=True)
    _run(p, value, size, color)


def _bullets(doc: Document, items) -> None:
    for item in items:
        p = doc.add_paragraph()
        _fmt(p, 0, 2, 12)
        p.paragraph_format.left_indent = Cm(0.7)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        _run(p, "—\t", 9, MUTED)
        _run(p, item, 9, INK)


# --------------------------------------------------------------------------- #
# Текст
# --------------------------------------------------------------------------- #
def _plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _num(value) -> str:
    return str(value).replace(".", ",")


def _signed(value: float) -> str:
    text = _num(value)
    return ("+" if value > 0 else "") + text


def _verdict(score: float, scanned: int | None = None) -> str:
    if scanned == 0:
        return "Документы не прочитаны: оценка не выставляется"
    if score >= 8:
        return "Документация в целом пригодна к проверке"
    if score >= 5:
        return "Требуются исправления до передачи"
    return "Существенные дефекты, требуется переработка"


def _verdict_inline(score: float, scanned: int | None = None) -> str:
    text = _verdict(score, scanned)
    return text[:1].lower() + text[1:]


def _score_color(score: float, scanned: int | None = None) -> str:
    if scanned == 0:
        return MUTED
    return GREEN if score >= 8 else GOLD_TEXT if score >= 5 else RED


def _tidy(text: str) -> str:
    def repl(match):
        n = int(match.group(1))
        return f" (встречается {n} {_plural(n, 'раз', 'раза', 'раз')})"

    return OCCURS.sub(repl, (text or "").strip())


def _sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    return text[:1].upper() + text[1:]


def _brief(text: str, limit: int = 90) -> str:
    text = re.sub(r"\s{2,}", " ", OCCURS.sub("", text or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0] or text[:limit]
    return cut.rstrip(" ,;:.") + "…"


def _files(f: dict) -> list[str]:
    raw = (f.get("file") or "").strip()
    return [x.strip() for x in raw.split(",") if x.strip()] or ["—"]


def _stem(name: str) -> str:
    path = Path(name)
    return path.stem if path.suffix else name


def _basename(raw: str) -> str:
    parts = [p for p in re.split(r"[\\/]", str(raw or "")) if p]
    return parts[-1] if parts else str(raw or "—")


def _doc_index(docs) -> dict[str, str]:
    return {
        Path(d.get("file", "")).stem.lower(): d["file"]
        for d in docs or []
        if d.get("file")
    }


def _display_file(name: str, index: dict[str, str]) -> str:
    return index.get(Path(name).stem.lower(), name)


def _location(f: dict, name: str) -> str:
    if f.get("page"):
        return f"{location_unit(name)} {f['page']}"
    return ""


def _where(f: dict, docs) -> str:
    index = _doc_index(docs)
    names = [_display_file(x, index) for x in _files(f)]
    if len(names) == 1:
        page = _location(f, names[0])
        return names[0] + (f", {page}" if page else "")
    return ", ".join(names)


def _address(f: dict, docs) -> tuple[str, str]:
    index = _doc_index(docs)
    names = [_display_file(x, index) for x in _files(f)]
    if len(names) == 1:
        return _stem(names[0]), _location(f, names[0])
    return _stem(names[0]), " + ".join(_stem(x) for x in names[1:])


def _norm_text(f: dict) -> str:
    norm = (f.get("norm") or "").strip()
    if norm:
        return norm
    if f.get("category") in ("заглушки", "комплект"):
        return "не требуется для этой проверки"
    return "—"


def _check_text(f: dict) -> str:
    category = f.get("category") or "—"
    return CAT_CHECK.get(category, category)


def _format_date(moment: datetime | None = None) -> str:
    return (moment or datetime.now()).strftime("%d.%m.%Y, %H:%M")


# --------------------------------------------------------------------------- #
# Обложка
# --------------------------------------------------------------------------- #
def _cover(doc: Document, meta: dict, summary: dict, docs) -> None:
    root_text = str(meta.get("root") or "—")
    obj = _basename(root_text)
    score = float(summary.get("score") or 0)
    files_total = int(meta.get("files_total") or 0)
    files_scanned = int(meta.get("files_scanned") or 0)
    chars = sum(int(d.get("chars") or 0) for d in docs or [])

    top = doc.add_table(rows=1, cols=2)
    _no_borders(top)
    left, right = top.rows[0].cells
    p = left.paragraphs[0]
    _fmt(p, 0, 0)
    if STAMP.exists():
        p.add_run().add_picture(str(STAMP), width=Cm(1.0))
    p = right.paragraphs[0]
    _fmt(p, 0, 0, align=WD_ALIGN_PARAGRAPH.RIGHT)
    _run(p, "ПРАВЕРАНА.BY", 8.5, INK, bold=True)
    _run(p, "  ·  РЕЕСТР ПРОВЕРКИ", 8, MUTED)
    p = right.add_paragraph()
    _fmt(p, 1, 0, align=WD_ALIGN_PARAGRAPH.RIGHT)
    _run(p, "ЧЕРНОВИК · НЕ ЗАКЛЮЧЕНИЕ", 7.5, MUTED)
    _fixed(top, (1.2, 15.8), pad_x=0, pad_y=0)

    _gap(doc, 30)
    p = doc.add_paragraph()
    _fmt(p, 0, 0, 1)
    _p_border(p, "bottom", INK, 6)

    _gap(doc, 34)
    p = doc.add_paragraph()
    _fmt(p, 0, 2)
    _run(p, "ОБЪЕКТ", 7, MUTED, bold=True)
    obj_size = 22 if len(obj) <= 28 else 18 if len(obj) <= 44 else 15
    p = doc.add_paragraph()
    _fmt(p, 0, 1, obj_size + 4)
    _run(p, obj, obj_size, INK, bold=True)
    p = doc.add_paragraph()
    _fmt(p, 0, 0, 11)
    _run(p, root_text, 8.5, MUTED)

    _gap(doc, 40)
    p = doc.add_paragraph()
    _fmt(p, 0, 2, 24)
    _run(p, "Отчёт об автоматизированной проверке проекта", 18, INK, bold=True)
    p = doc.add_paragraph()
    _fmt(p, 0, 0, 13)
    _run(p, "Реестр замечаний с адресами, нормами и действиями", 10.5, MUTED)

    _gap(doc, 100)
    corpus = (meta.get("corpus") or "дата не определена").strip()
    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", corpus):
        base = f"реестр ТНПА, редакция {corpus}"
    else:
        base = f"реестр ТНПА: {corpus}"
    rows = (
        ("Дата отчёта", _format_date()),
        ("База ТНПА", base),
        ("Папка", root_text),
        ("Состав", f"{files_total} {_plural(files_total, 'файл', 'файла', 'файлов')}"
                   f" · {_num(meta.get('size_mb', 0))} МБ"),
        ("Прочитано", f"{files_scanned} из {files_total} файлов · {chars} знаков"
                      f" · {_num(meta.get('duration_s', 0))} с"),
        ("Статус", "Черновик · не заключение"),
    )
    table = doc.add_table(rows=0, cols=2)
    _no_borders(table)
    for label, value in rows:
        cells = table.add_row().cells
        for cell in cells:
            _cell_border(cell, "bottom", LINE, 4)
        p = cells[0].paragraphs[0]
        _fmt(p, 0, 0, 11)
        _run(p, label.upper(), 7, MUTED, bold=True)
        p = cells[1].paragraphs[0]
        _fmt(p, 0, 0, 11)
        _run(p, value, 9.5, INK)
    _fixed(table, (4.2, 12.8), pad_y=0.12)

    if docs:
        _gap(doc, 18)
        p = doc.add_paragraph()
        _fmt(p, 0, 3, 10)
        _run(p, f"ПРОЧИТАНО · {len(docs)} "
                f"{_plural(len(docs), 'ДОКУМЕНТ', 'ДОКУМЕНТА', 'ДОКУМЕНТОВ')}",
             7, MUTED, bold=True)
        shown = docs[:12]
        cols = 3
        rows = (len(shown) + cols - 1) // cols
        grid = doc.add_table(rows=rows, cols=cols)
        _no_borders(grid)
        for i, d in enumerate(shown):
            cell = grid.rows[i // cols].cells[i % cols]
            p = cell.paragraphs[0]
            _fmt(p, 0, 0, 10)
            _run(p, _stem(d.get("file", "—")), 8, INK)
        _fixed(grid, (5.67, 5.67, 5.66), pad_x=0, pad_y=0)
        if len(docs) > 12:
            p = doc.add_paragraph()
            _fmt(p, 1, 0, 10)
            _run(p, f"…и ещё {len(docs) - 12} документов", 7.5, MUTED)

    _gap(doc, 40)
    p = doc.add_paragraph()
    _fmt(p, 12, 0, 24)
    _p_border(p, "top", LINE, 4)
    verdict_size = 16 if files_scanned == 0 else 20
    _run(p, _verdict(score, files_scanned), verdict_size,
         _score_color(score, files_scanned), bold=True)
    p = doc.add_paragraph()
    _fmt(p, 2, 0, 12)
    if files_scanned == 0:
        _run(p, "Оценка не выставляется", 9, MUTED)
    else:
        _run(p, f"Оценка {_num(score)} из 10", 9, MUTED)
    _run(p, "  ·  ", 9, MUTED)
    counts = (
        (summary.get("error", 0), "ошибка", "ошибки", "ошибок"),
        (summary.get("warn", 0), "предупреждение", "предупреждения", "предупреждений"),
        (summary.get("info", 0), "примечание", "примечания", "примечаний"),
    )
    for i, (count, one, few, many) in enumerate(counts):
        if i:
            _run(p, " · ", 9, MUTED)
        _run(p, f"{count} {_plural(int(count), one, few, many)}", 9, MUTED)

    _gap(doc, 100)
    p = doc.add_paragraph()
    _fmt(p, 0, 0, 12)
    _p_border(p, "top", LINE, 4)
    _run(p, "Далее: указатель замечаний · карточки с адресом и нормой · "
            "порядок проверки · прочитанные документы", 8, MUTED)


# --------------------------------------------------------------------------- #
# Указатель
# --------------------------------------------------------------------------- #
def _register(doc: Document, result: dict) -> None:
    meta, summary = result.get("meta", {}), result.get("summary", {})
    findings = result.get("findings", [])
    docs = result.get("documents", [])
    score = float(summary.get("score") or 0)
    files_scanned = int(meta.get("files_scanned") or 0)

    _heading(doc, "1 Указатель замечаний", 1, new_page=True)

    unique = {_stem(x).lower() for f in findings for x in _files(f)}
    p = doc.add_paragraph()
    _fmt(p, 0, 2, 14)
    _run(p, f"{len(findings)} {_plural(len(findings), 'замечание', 'замечания', 'замечаний')}",
         10, INK, bold=True)
    _run(p, f" в {len(unique)} {_plural(len(unique), 'файле', 'файлах', 'файлах')}", 10, INK)
    _run(p, ". ", 10, INK)
    for i, key in enumerate(("error", "warn", "info")):
        if i:
            _run(p, " · ", 9, MUTED)
        count = int(summary.get(key) or 0)
        one, few, many = {
            "error": ("ошибка", "ошибки", "ошибок"),
            "warn": ("предупреждение", "предупреждения", "предупреждений"),
            "info": ("примечание", "примечания", "примечаний"),
        }[key]
        _run(p, str(count), 9, INK, bold=True)
        _run(p, " " + _plural(count, one, few, many), 9, SEV_COLOR[key], bold=True)
    _run(p, ".", 9, INK)

    p = doc.add_paragraph()
    _fmt(p, 0, 2, 13)
    if files_scanned == 0:
        _run(p, "Оценка не выставляется — ", 9.5, INK)
    else:
        _run(p, f"Оценка {_num(score)} из 10 — ", 9.5, INK)
    _run(p, _verdict_inline(score, files_scanned), 9.5,
         _score_color(score, files_scanned))
    _run(p, ".", 9.5, INK)

    by_cat: dict[str, int] = {}
    for f in findings:
        category = f.get("category") or "—"
        by_cat[category] = by_cat.get(category, 0) + 1
    order = [c for c in CAT_ORDER if c in by_cat] + \
            [c for c in by_cat if c not in CAT_ORDER]
    if order:
        p = doc.add_paragraph()
        _fmt(p, 0, 8, 12)
        _run(p, "Проверки: ", 8.5, MUTED)
        _run(p, " · ".join(
            f"{CAT_CHECK.get(c, c)} — {by_cat[c]}" for c in order), 8.5, MUTED)

    if findings:
        table = doc.add_table(rows=1, cols=4)
        _table_borders(table, {
            "top": ("single", 6, INK),
            "bottom": ("single", 6, INK),
        })
        headers = ("№", "АДРЕС", "СУТЬ", "НОРМА")
        aligns = (WD_ALIGN_PARAGRAPH.CENTER, None, None, None)
        header = table.rows[0]
        header._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        header._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i, text in enumerate(headers):
            cell = header.cells[i]
            p = cell.paragraphs[0]
            _fmt(p, 3, 3, 10, align=aligns[i])
            _run(p, text, 7, MUTED, bold=True)
            _cell_border(cell, "bottom", LINE_STRONG, 8)

        for number, f in enumerate(findings, 1):
            row = table.add_row()
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            cells = row.cells
            for cell in cells:
                cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
                _cell_border(cell, "bottom", LINE, 4)

            _cell_border(cells[0], "left", SEV_COLOR.get(f.get("severity"), SLATE),
                         SEV_TICK.get(f.get("severity"), 6))
            p = cells[0].paragraphs[0]
            _fmt(p, 3, 3, 11, align=WD_ALIGN_PARAGRAPH.CENTER)
            _run(p, f"З-{number:02d}", 8, INK, bold=True)

            address, place = _address(f, docs)
            p = cells[1].paragraphs[0]
            _fmt(p, 3, 0, 11)
            _run(p, address, 8, INK, bold=True)
            if place:
                p2 = cells[1].add_paragraph()
                _fmt(p2, 0, 3, 10)
                _run(p2, place, 7.5, MUTED)
            else:
                p.paragraph_format.space_after = Pt(3)

            p = cells[2].paragraphs[0]
            _fmt(p, 3, 3, 11)
            _run(p, _brief(f.get("message", "")), 8.5, INK)

            norm = (f.get("norm") or "").strip()
            p = cells[3].paragraphs[0]
            _fmt(p, 3, 3, 11)
            _run(p, norm or "—", 8, INK if norm else MUTED)

        _fixed(table, (1.1, 3.6, 7.0, 5.3), pad_y=0.1)
        _gap(doc, 6)
        p = doc.add_paragraph()
        _fmt(p, 0, 6, 11)
        _run(p, "Тик слева: 3 pt — ошибка, 1,5 pt — предупреждение, "
                "0,75 pt — примечание. Слово уровня стоит рядом с номером, "
                "чтобы смысл сохранялся в чёрно-белой печати.", 7.5, MUTED)
    else:
        p = doc.add_paragraph()
        _fmt(p, 0, 8, 14)
        _run(p, "Замечаний не выявлено выполненными проверками.", 10, INK)

    files_total = int(meta.get("files_total") or 0)
    chars = sum(int(d.get("chars") or 0) for d in docs)
    unread = max(0, files_total - files_scanned)
    truncated = int(meta.get("truncated") or 0)
    p = doc.add_paragraph()
    _fmt(p, 0, 4, 12)
    _run(p, "Покрытие: ", 8.5, MUTED, bold=True)
    _run(p, f"прочитано {files_scanned} из {files_total} файлов, {chars} знаков", 8.5, MUTED)
    if unread:
        _run(p, f"; не прочитано {unread} "
                f"{_plural(unread, 'файл', 'файла', 'файлов')}", 8.5, MUTED)
        if truncated:
            _run(p, f", из них {truncated} — предел", 8.5, MUTED)
    _run(p, ". Оценка считается только по прочитанному.", 8.5, MUTED)

    prev = (result.get("history") or {}).get("previous")
    if prev:
        d = prev["delta"]
        p = doc.add_paragraph()
        _fmt(p, 0, 6, 12)
        _run(p, "С прошлого прогона: ", 8.5, MUTED)
        _run(p, f"оценка {_num(prev['old']['score'])} → {_num(prev['new']['score'])} "
                f"({_signed(d['score'])}) · ошибки {prev['old']['error']} → "
                f"{prev['new']['error']} ({_signed(d['error'])})", 8.5, INK)
        if prev.get("scope_changed"):
            _run(p, f". Состав выборки изменился: {prev['files_old']} → "
                    f"{prev['files_new']} файлов; сравнение условное", 8.5, MUTED)

    _heading(doc, "Что не проверялось", 2)
    _bullets(doc, (
        "Сканы без OCR, DWG, RVT, XLSX и DOC: читается только текст DOCX и PDF.",
        "Расчёты, армирование, нагрузки, пожарная безопасность и сметы.",
        "Пункты норм — по индексу фонда: «не найден» значит «нет в проиндексированном "
        "тексте», а не «отменён».",
        "Комплектность — по именам файлов; нестандартные имена дают ложные срабатывания.",
        "В PDF комментарии не добавляются; разметка — только DOCX, первые вхождения "
        "(до трёх на шифр).",
    ))


# --------------------------------------------------------------------------- #
# Карточки
# --------------------------------------------------------------------------- #
def _cards(doc: Document, findings, docs) -> None:
    _heading(doc, "2 Карточки замечаний", 1, new_page=True)
    p = doc.add_paragraph()
    _fmt(p, 0, 10, 13)
    _run(p, "Нумерация совпадает с указателем. В каждой карточке — место, "
            "норма и действие.", 9.5, MUTED)

    if not findings:
        p = doc.add_paragraph()
        _run(p, "Замечаний нет: карточки не сформированы.", 10, INK)
        return

    for number, f in enumerate(findings, 1):
        severity = f.get("severity") if f.get("severity") in SEV_LABEL else "info"
        table = doc.add_table(rows=1, cols=2)
        _table_borders(table, {"top": ("single", 4, LINE)})
        row = table.rows[0]
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        left, right = row.cells
        left.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        right.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        _cell_border(left, "left", SEV_COLOR[severity], SEV_TICK[severity])

        p = left.paragraphs[0]
        _fmt(p, 4, 0, 12)
        _run(p, f"З-{number:02d}", 10.5, INK, bold=True)
        p = left.add_paragraph()
        _fmt(p, 0, 4, 10)
        _run(p, SEV_LABEL[severity], 7.5, SEV_COLOR[severity], bold=True)

        p = right.paragraphs[0]
        _fmt(p, 4, 4, 14)
        _run(p, _sentence(_tidy(f.get("message", ""))), 11, INK, bold=True)

        p = right.add_paragraph()
        _fmt(p, 0, 1.5, 12.5)
        _label_value(p, "Где", _where(f, docs))

        p = right.add_paragraph()
        _fmt(p, 0, 1.5, 12.5)
        _label_value(p, "Норма", _norm_text(f))

        p = right.add_paragraph()
        _fmt(p, 0, 1.5, 12.5)
        _label_value(p, "Действие", (f.get("action") or "—").strip())

        p = right.add_paragraph()
        _fmt(p, 0, 4, 11)
        _run(p, "ЧЕМ ПРОВЕРЕНО · ", 7, MUTED, bold=True)
        _run(p, _check_text(f), 8, MUTED)

        _fixed(table, (2.6, 14.4), pad_y=0.1)
        _gap(doc, 5)


# --------------------------------------------------------------------------- #
# Порядок проверки, разметка
# --------------------------------------------------------------------------- #
def _method(doc: Document, meta: dict, marked) -> None:
    _heading(doc, "3 Как проверить замечание", 1)
    p = doc.add_paragraph()
    _fmt(p, 0, 8, 14)
    _run(p, "Каждая строка указателя проверяется за три шага.", 10, INK)

    corpus = (meta.get("corpus") or "дата не определена").strip()
    steps = (
        ("Откройте место.",
         "В карточке «Где» — файл и фрагмент для DOCX или страница для PDF. "
         "Номер фрагмента — порядок извлечённого текста, а не страница вёрстки."),
        ("Сверьте норму.",
         f"В строке «Норма» — документ и пункт; статус документа — в реестре "
         f"ТНПА от {corpus}. Если пункт не найден в индексе фонда, это значит "
         f"«нет в проиндексированном тексте», а не «отменён»."),
        ("Подтвердите или снимите.",
         "Если замечание подтверждается — выполните действие. Если нет — "
         "пометьте его ложным: отчёт показывает только то, что нашёл в "
         "извлечённом тексте, и не заменяет решение проверяющего."),
    )
    table = doc.add_table(rows=0, cols=2)
    _no_borders(table)
    for i, (title, text) in enumerate(steps, 1):
        cells = table.add_row().cells
        p = cells[0].paragraphs[0]
        _fmt(p, 0, 6, 14)
        _run(p, f"{i}.", 10, INK, bold=True)
        p = cells[1].paragraphs[0]
        _fmt(p, 0, 6, 14)
        _run(p, title, 10, INK, bold=True)
        _run(p, " " + text, 10, INK)
    _fixed(table, (0.9, 16.1), pad_x=0, pad_y=0)

    _heading(doc, "Разметка документов", 2)
    _marking(doc, marked)


def _marking(doc: Document, marked) -> None:
    if not marked:
        p = doc.add_paragraph()
        _fmt(p, 0, 0, 13)
        _run(p, "Разметка не запрашивалась.", 9.5, MUTED)
        return

    placed = [m for m in marked if m.get("comments")]
    failed = [m for m in marked if m.get("error")]
    if placed:
        p = doc.add_paragraph()
        _fmt(p, 0, 4, 13)
        _run(p, "Копии документов с комментариями Word: ошибки — красным, "
                "предупреждения — жёлтым, примечания — бирюзовым. "
                "Архив — praverana-marked.zip.", 9.5, INK)
        table = doc.add_table(rows=1, cols=2)
        _table_borders(table, {"top": ("single", 6, INK),
                               "bottom": ("single", 6, INK)})
        for i, text in enumerate(("ФАЙЛ", "КОММЕНТАРИЕВ")):
            cell = table.rows[0].cells[i]
            p = cell.paragraphs[0]
            _fmt(p, 2, 2, 10, align=WD_ALIGN_PARAGRAPH.RIGHT if i else None)
            _run(p, text, 7, MUTED, bold=True)
            _cell_border(cell, "bottom", LINE_STRONG, 8)
        for m in placed:
            row = table.add_row()
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            p = row.cells[0].paragraphs[0]
            _fmt(p, 2, 2, 11)
            _run(p, m.get("file", "—"), 8.5, INK)
            p = row.cells[1].paragraphs[0]
            _fmt(p, 2, 2, 11, align=WD_ALIGN_PARAGRAPH.RIGHT)
            _run(p, str(m.get("comments", 0)), 8.5, INK)
            for cell in row.cells:
                _cell_border(cell, "bottom", LINE, 4)
        _fixed(table, (14.5, 2.5), pad_y=0.08)
        _gap(doc, 6)
    if failed:
        p = doc.add_paragraph()
        _fmt(p, 0, 4, 12)
        _run(p, "Не удалось разметить: " + "; ".join(
            f"{m.get('file', '—')} ({m.get('error', 'ошибка')})" for m in failed),
            8.5, INK)
    if not placed and not failed:
        p = doc.add_paragraph()
        _fmt(p, 0, 4, 13)
        _run(p, "В проекте нет DOCX-документов, к которым привязаны замечания.",
             9.5, MUTED)


# --------------------------------------------------------------------------- #
# Документы и решение
# --------------------------------------------------------------------------- #
def _documents(doc: Document, meta: dict, docs) -> None:
    _heading(doc, "4 Прочитанные документы", 1)
    if not docs:
        p = doc.add_paragraph()
        _run(p, "Текстовые документы не прочитаны.", 10, INK)
        return

    p = doc.add_paragraph()
    _fmt(p, 0, 6, 13)
    chars = sum(int(d.get("chars") or 0) for d in docs)
    _run(p, f"Текст извлечён из {len(docs)} "
            f"{_plural(len(docs), 'файла', 'файлов', 'файлов')} · {chars} знаков.",
         9, MUTED)

    rows = docs[:40]
    table = doc.add_table(rows=1, cols=4)
    _table_borders(table, {"top": ("single", 6, INK),
                           "bottom": ("single", 6, INK)})
    headers = ("№", "ФАЙЛ", "СТР./ФРАГМ.", "ЗНАКОВ")
    aligns = (WD_ALIGN_PARAGRAPH.CENTER, None, WD_ALIGN_PARAGRAPH.RIGHT,
              WD_ALIGN_PARAGRAPH.RIGHT)
    header = table.rows[0]
    header._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    header._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    for i, text in enumerate(headers):
        cell = header.cells[i]
        p = cell.paragraphs[0]
        _fmt(p, 3, 3, 10, align=aligns[i])
        _run(p, text, 7, MUTED, bold=True)
        _cell_border(cell, "bottom", LINE_STRONG, 8)
    for number, d in enumerate(rows, 1):
        row = table.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        values = (number, d.get("file", "—"), d.get("pages", 0), d.get("chars", 0))
        for i, value in enumerate(values):
            cell = row.cells[i]
            p = cell.paragraphs[0]
            _fmt(p, 2, 2, 11, align=aligns[i])
            _run(p, str(value), 8.5, INK)
            _cell_border(cell, "bottom", LINE, 4)
    _fixed(table, (0.9, 9.6, 3.2, 3.3), pad_y=0.08)

    unread = max(0, int(meta.get("files_total") or 0) - int(meta.get("files_scanned") or 0))
    truncated = int(meta.get("truncated") or 0)
    p = doc.add_paragraph()
    _fmt(p, 6, 0, 12)
    tail = f"Не прочитаны {unread} {_plural(unread, 'файл', 'файла', 'файлов')}: " \
           "нет извлекаемого текста, неподдерживаемый формат" \
           + (f" или не вошли в лимит ({truncated})" if truncated else "") + "." if unread else ""
    _run(p, f"Итого: {len(docs)} {_plural(len(docs), 'файл', 'файла', 'файлов')} · "
            f"{chars} знаков. {tail}", 8.5, MUTED)
    if len(docs) > 40:
        p = doc.add_paragraph()
        _fmt(p, 2, 0, 11)
        _run(p, f"…и ещё {len(docs) - 40} файлов — в панели аудита.", 8.5, MUTED)


# --------------------------------------------------------------------------- #
def _setup(doc: Document) -> None:
    for style in doc.styles:
        try:
            _font(style, "Times New Roman")
        except (AttributeError, KeyError):
            continue

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10)
    normal.paragraph_format.line_spacing = Pt(14)
    normal.paragraph_format.space_after = Pt(0)

    h1 = doc.styles["Heading 1"]
    h1.font.name = "Times New Roman"
    h1.font.size = Pt(14)
    h1.font.bold = True
    h1.font.color.rgb = _rgb(INK)
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    h1.paragraph_format.keep_with_next = True

    h2 = doc.styles["Heading 2"]
    h2.font.name = "Times New Roman"
    h2.font.size = Pt(11.5)
    h2.font.bold = True
    h2.font.color.rgb = _rgb(INK)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(3)
    h2.paragraph_format.keep_with_next = True

    for name in ("Header", "Footer"):
        try:
            doc.styles[name].paragraph_format.tab_stops.clear_all()
        except KeyError:
            pass

    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(1.5)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.8)
    sec.header_distance = Cm(1.0)
    sec.footer_distance = Cm(0.9)
    sec.different_first_page_header_footer = True

    header = sec.header.paragraphs[0]
    header.text = ""
    _fmt(header, 0, 0)
    header.paragraph_format.tab_stops.clear_all()
    header.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), WD_TAB_ALIGNMENT.RIGHT)
    _run(header, "Праверана.by", 8, INK, bold=True)
    _run(header, "  ·  реестр проверки", 8, MUTED)
    _run(header, "\tЧерновик · не заключение", 7.5, MUTED)
    _p_border(header, "bottom", LINE, 4)

    footer = sec.footer.paragraphs[0]
    footer.text = ""
    _fmt(footer, 0, 0)
    footer.paragraph_format.tab_stops.clear_all()
    footer.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), WD_TAB_ALIGNMENT.RIGHT)
    _run(footer, "Праверана.by · отчёт об автоматизированной проверке", 7.5, MUTED)
    _run(footer, "\tстр. ", 7.5, MUTED)
    _field(footer, "PAGE")
    _run(footer, " из ", 7.5, MUTED)
    _field(footer, "NUMPAGES")

    sec.first_page_header.paragraphs[0].text = ""
    sec.first_page_footer.paragraphs[0].text = ""


def build_docx(result: dict, out: Path, marked: list[dict] | None = None) -> Path:
    meta = result.get("meta", {})
    summary = result.get("summary", {})
    findings = result.get("findings", [])
    docs = result.get("documents", [])

    doc = Document()
    _setup(doc)
    doc.core_properties.title = "Отчёт об автоматизированной проверке проекта"
    doc.core_properties.author = "Праверана.by"
    doc.core_properties.subject = _basename(meta.get("root") or "")
    doc.core_properties.comments = "Черновик · не заключение"

    _cover(doc, meta, summary, docs)
    _register(doc, result)
    _cards(doc, findings, docs)
    _method(doc, meta, marked)
    _documents(doc, meta, docs)

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
        $doc.Fields.Update() | Out-Null
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
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"docx": str(docx_path), "pdf": str(pdf_path)}]
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "cfg.json"
        cfg.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        ps = Path(td) / "export.ps1"
        ps.write_text(PS_SCRIPT, encoding="utf-8")
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(ps), str(cfg)],
            check=True, capture_output=True, timeout=180,
        )
    if not pdf_path.exists():
        raise RuntimeError("PDF не создан")
    return pdf_path
