"""Общие утилиты: нормализация шифров, извлечение текста, страницы.

Никакой арифметики «в голове»: всё, что можно посчитать, считается здесь или в checks.py.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

CORPUS_DEFAULT = Path.home() / "Desktop" / "Нормы-Беларусь-2026"
REGISTRY_DEFAULT = "02-Реестр.csv"
REGISTRY_DATE = "18.11.2026"
STATUS_FIELD = "Статус"
STATUS_PREFIX = "статус на"
STATUS_RE = re.compile(r"^статус(?:\s+на\s+\d{1,2}\.\d{1,2}\.\d{4})?$")

TEXT_SUFFIXES = {".md", ".txt", ".csv"}
SUPPORTED = TEXT_SUFFIXES | {".pdf", ".docx", ".xlsx"}

_DASH = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_SPACE = dict.fromkeys(map(ord, "\u00a0\u202f\t"), " ")

PREFIXES = ("СНиП", "СНБ", "СТБ EN", "СТБ ISO", "СТБ", "ТКП EN", "ТКП", "СН", "СП",
            "ПУЭ", "ГОСТ Р", "ГОСТ ISO", "ГОСТ")
CANON = {p.upper(): p for p in PREFIXES}
PREFIX_RE = re.compile(
    r"^(СНИП|СНБ|СТБ(?:\s*(?:EN|ISO))?|ТКП(?:\s*EN)?|СН|СП|ПУЭ|ГОСТ(?:\s*(?:ISO|IEC|Р))?)",
    re.IGNORECASE
)

CODE_RE = re.compile(
    r"(?<![А-ЯЁA-Z])(СНиП|СНБ|СТБ(?:\s*(?:EN|ISO))?|ТКП(?:\s*EN)?|СН|СП|ПУЭ|ГОСТ(?:\s*(?:ISO|IEC|Р))?)\s*"
    r"(\d+(?:[.\-]\d+)*(?:-\d{2,4})?|[IVX]+-\d+(?:[.\-]\d+)*)(\*?)",
    re.IGNORECASE,
)

# Шифры, которые нельзя применять в РБ (пост. МАиС № 7 от 21.01.2025 и замены 2025–2026).
CURATED_OUTDATED = {
    "СНБ 2.04.02-2000": ("СП 2.04.04-2026", "утратила силу с 01.07.2026"),
    "ТКП 45-2.02-110-2008": ("СП 2.02.05-2026", "отменён с 01.11.2026"),
    "ТКП 45-2.02-142-2011": ("СН 2.02.05-2020", "отменён с 01.09.2018"),
    "ТКП 45-2.02-315-2008": ("СН 2.02.05-2020", "такого документа не существует (только -2018)"),
    "ТКП 45-2.02-315-2011": ("СН 2.02.05-2020", "такого документа не существует (только -2018)"),
    "ПУЭ 6": ("ТКП 339-2022", "ПУЭ 6 изд. в РБ не применяются"),
    "ТКП 339-2011": ("ТКП 339-2022", "заменён"),
    "ГОСТ 27751-88": ("ГОСТ 27751-2014", "заменён с 01.05.2026 (пост. Госстандарта № 156 от 27.11.2025)"),
    "СТБ 2331-2015": ("СН 3.02.07-2020", "отменён с 10.06.2021"),
    "ТКП 45-2.02-315-2018": ("СН 2.02.05-2020", "отменён с 04.04.2021 (пост. МАиС № 25 от 24.03.2021)"),
}


def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return text.translate(_DASH).translate(_SPACE)


def status_key(row: dict) -> str | None:
    """Имя колонки статуса: «Статус» или «Статус на <дата>»."""
    for key in row:
        if not key:
            continue
        name = str(key).strip().lower()
        if STATUS_RE.match(name):
            return key
    return None


def status_of(row: dict) -> str:
    key = status_key(row)
    return (row.get(key) or "").strip() if key else ""


def norm_code(raw: str) -> str:
    """Канонический вид ссылки: «сн 2.01.04 - 2025*» → «СН 2.01.04-2025»."""
    s = clean(raw).upper().replace("*", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s*\.\s*", ".", s)
    m = PREFIX_RE.match(s)
    if m:
        prefix = m.group(1)
        rest = s[m.end():].strip()
        canonical = CANON.get(prefix, prefix)
        if prefix == "СТБ" and rest.upper().startswith("EN"):
            canonical, rest = "СТБ EN", rest[2:].strip()
        s = f"{canonical} {rest}".strip()
    return re.sub(r"\s+", " ", s).strip()


def year_of(code: str) -> int | None:
    m = re.search(r"-(\d{2,4})$", code)
    if not m:
        return None
    digits = m.group(1)
    if len(digits) == 3:
        return None  # трёхзначный «год» — это опечатка шифра, а не редакция
    y = int(digits)
    if len(digits) == 4:
        return y
    return 2000 + y if y <= 30 else 1900 + y


def extract_citations(text: str) -> list[dict]:
    """Все ссылки на ТНПА в тексте с номером строки и контекстом вокруг шифра."""
    out: list[dict] = []
    for lineno, line in enumerate(clean(text).splitlines(), 1):
        for m in CODE_RE.finditer(line):
            code = norm_code(m.group(0))
            if len(code.split()) < 2:
                continue
            # Окно вокруг шифра, а не первые 240 знаков строки: в длинном абзаце
            # «шифр … п. X» иначе терялся, и пункт не проверялся.
            start = max(0, m.start() - 40)
            end = min(len(line), m.end() + 180)
            out.append({
                "code": code,
                "line": lineno,
                "context": line[start:end].strip(),
            })
    return out


def read_text(path: Path) -> str:
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _pdf_pages(path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def _docx_pages(path: Path) -> list[str]:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return ["\n".join(parts)]


def _xlsx_pages(path: Path) -> list[str]:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), read_only=True, data_only=True)
    out: list[str] = []
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v) for v in row]
            if any(cells):
                rows.append(" | ".join(cells))
        out.append(f"### Лист: {ws.title}\n" + "\n".join(rows))
    return out


def pages_of(path: Path) -> list[str]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return [read_text(path)]
    if suffix == ".pdf":
        return _pdf_pages(path)
    if suffix == ".docx":
        return _docx_pages(path)
    if suffix == ".xlsx":
        return _xlsx_pages(path)
    raise ValueError(f"unsupported: {suffix}")


def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def short(text: str, limit: int = 200) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
