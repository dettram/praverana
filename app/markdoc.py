"""Разметка исходных DOCX: комментарии Word и подсветка найденных мест.

  from markdoc import mark_document
  mark_document(src, dst, marks)

marks: [{"text": "ГОСТ 24045-2016", "severity": "warn", "message": "нет в реестре"}]
Ищется точное вхождение (без учёта регистра) в абзацах и таблицах; на найденный
фрагмент ставится комментарий и подсветка. Документ не меняется, сохраняется копия.
"""
from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.run import Run

COLOR = {"error": WD_COLOR_INDEX.RED, "warn": WD_COLOR_INDEX.YELLOW,
         "info": WD_COLOR_INDEX.TURQUOISE}
AUTHOR = "Аудит проекта"


def _set_text(run_el, text: str) -> None:
    for t in run_el.findall(qn("w:t")):
        run_el.remove(t)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    run_el.append(t)


def _split_run(run: Run, pos: int):
    """Делит run на два по смещению pos; возвращает (левый, правый)."""
    text = run.text
    if pos <= 0:
        return None, run
    if pos >= len(text):
        return run, None
    new_r = copy.deepcopy(run._r)
    run._r.addnext(new_r)
    _set_text(run._r, text[:pos])
    _set_text(new_r, text[pos:])
    return run, Run(new_r, run._parent)


def _table_paragraphs(table):
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                yield p
            for nested in cell.tables:
                yield from _table_paragraphs(nested)


def _part_paragraphs(part):
    for p in part.paragraphs:
        yield p
    for table in part.tables:
        yield from _table_paragraphs(table)


def _paragraphs(doc: Document):
    seen = set()

    def unique(paragraphs):
        for p in paragraphs:
            marker = id(p._p)
            if marker in seen:
                continue
            seen.add(marker)
            yield p

    yield from unique(doc.paragraphs)
    for table in doc.tables:
        yield from unique(_table_paragraphs(table))
    for section in doc.sections:
        for part in (section.header, section.footer, section.first_page_header,
                     section.first_page_footer, section.even_page_header,
                     section.even_page_footer):
            yield from unique(_part_paragraphs(part))


def _comment_span(doc: Document, paragraph, start: int, end: int, text: str,
                  severity: str) -> bool:
    """Ставит комментарий на символы [start, end) абзаца."""
    # разрезаем так, чтобы границы попали на границы runs
    for _ in range(2):
        offset = 0
        for run in list(paragraph.runs):
            length = len(run.text)
            if offset < start < offset + length:
                _split_run(run, start - offset)
                break
            offset += length
        offset = 0
        for run in list(paragraph.runs):
            length = len(run.text)
            if offset < end < offset + length:
                _split_run(run, end - offset)
                break
            offset += length

    target = []
    offset = 0
    for run in paragraph.runs:
        length = len(run.text)
        if length and offset >= start and offset + length <= end:
            target.append(run)
        offset += length
    if not target:
        return False
    color = COLOR.get(severity, WD_COLOR_INDEX.YELLOW)
    for run in target:
        run.font.highlight_color = color
    doc.add_comment(target, text=text, author=AUTHOR, initials="АП")
    return True


def mark_document(src: Path, dst: Path, marks: list[dict], limit: int = 80) -> dict:
    """Копирует документ и размечает до limit совпадений. Возвращает статистику."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    doc = Document(str(src))
    done = {m["text"]: 0 for m in marks}
    placed = 0
    paragraphs = list(_paragraphs(doc))
    for mark in marks:
        needle = mark["text"]
        if not needle or done[needle] >= 3 or placed >= limit:
            continue
        pattern = re.compile(re.escape(needle), re.IGNORECASE)
        for p in paragraphs:
            hay = p.text
            if not hay:
                continue
            for m in pattern.finditer(hay):
                end = m.end()
                # «ГОСТ 27751» не должен совпадать с «ГОСТ 27751-2014».
                if end < len(hay) and (hay[end].isdigit() or hay[end] == "-"):
                    continue
                if _comment_span(doc, p, m.start(), end,
                                 f"{mark['message']} (найдено автоматически)",
                                 mark["severity"]):
                    done[needle] += 1
                    placed += 1
                if done[needle] >= 3 or placed >= limit:
                    break
            if done[needle] >= 3 or placed >= limit:
                break
    if placed:
        doc.save(str(dst))
    else:
        shutil.copy2(src, dst)
    return {"comments": placed, "file": dst.name}


def collect_marks(result: dict, root: Path) -> dict[str, list[dict]]:
    """Из результата аудита собирает, что и где помечать в DOCX."""
    out: dict[str, list[dict]] = {}
    for f in result.get("findings", []):
        raw_files = f.get("files") or (f.get("file") or "").split(",")
        if isinstance(raw_files, str):
            raw_files = raw_files.split(",")
        filenames = []
        for raw in raw_files:
            file = (raw or "").strip()
            if file == "—" or not file:
                continue
            if not file.lower().endswith(".docx"):
                candidate = file + ".docx"
                if (root / candidate).exists():
                    file = candidate
                else:
                    continue
            if (root / file).exists():
                filenames.append(file)
        if not filenames:
            continue
        text = (f.get("norm") or "").split(",")[0].strip()
        if not text:
            msg = f.get("message", "")
            if "«" in msg and "»" in msg:
                text = msg.split("«")[1].split("»")[0]
        if not text:
            continue
        mark = {
            "text": text,
            "severity": f["severity"],
            "message": f"{f['category']}: {f['message']}",
        }
        for file in filenames:
            out.setdefault(file, []).append(mark)
    return out


def mark_all(result: dict, root: Path, out_dir: Path) -> list[dict]:
    """Размечает все DOCX из результата. Возвращает список отчётов по файлам."""
    reports = []
    for rel, marks in collect_marks(result, root).items():
        src = root / rel
        if not src.exists():
            continue
        dst = out_dir / rel
        try:
            stats = mark_document(src, dst, marks)
        except Exception as exc:  # noqa: BLE001
            reports.append({"file": rel, "error": f"{type(exc).__name__}: {exc}"})
            continue
        reports.append({**stats, "file": rel, "marks": len(marks)})
    return reports
