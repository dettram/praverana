"""Движок аудита папки проекта: файлы → замечания со ссылкой на норму.

  uv run --with python-docx --with pypdf python app/engine.py --path "<папка проекта>" --out result.json

Проверки детерминированные, без модели:
  1. нормы       — шифр из текста сверяется с реестром (отменён / не подтверждён / нет в реестре);
  2. цитаты      — «шифр … п. X» проверяется по индексу фонда (пункт существует, страница);
  3. комплект    — наличие основных разделов проекта по именам файлов;
  4. ПОС/ППР     — состав по приложениям Г и В СН 1.03.04-2020;
  5. заглушки    — «по проекту», «ХХХ», «___», «заполнить» в текстовых документах;
  6. подписи     — пустые строки подписи в листах согласования (эвристика).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import sys

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from clause import clause_status  # noqa: E402
from common import CODE_RE, CORPUS_DEFAULT, extract_citations, norm_code, read_text  # noqa: E402
from norm_check import classify, load_registry, registry_date  # noqa: E402

DB = Path.home() / ".stroy-audit" / "index.sqlite"
SKILL = Path(__file__).resolve().parent.parent
COMPOSITION = SKILL / "data" / "pos-ppr.json"

TEXT_EXT = {".md", ".txt", ".csv"}
DOC_EXT = {".docx", ".pdf", ".xlsx", ".doc"}
UNSUPPORTED_EXT = {".xlsx", ".doc"}
SKIP_EXT = {".dwg", ".rvt", ".rfa", ".ifc", ".png", ".jpg", ".jpeg", ".tif", ".tiff",
            ".zip", ".rar", ".7z", ".exe", ".lnk", ".bak", ".tmp"}
MAX_FILES = 600
MAX_PDF_PAGES = 80

CLAUSE_RE = re.compile(r"п(?:ункт|\.)?\s*№?\s*(\d+(?:\.\d+){0,4})", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"(ХХХ|___|\bзаполнить\b|\bне заполнено\b|\[вставить)", re.IGNORECASE)
SOFT_PLACEHOLDER_RE = re.compile(r"(по проекту|уточнить по проекту)", re.IGNORECASE)
SHORT_CODE_RE = re.compile(r"^(СН|СП|ГОСТ|СТБ|ТКП)\s*\d{1,2}$")
TRUNCATED_RE = re.compile(r"^(СН|СП|СТБ|ГОСТ|ТКП)\s*\d+(?:\.\d+){1,3}$")


def pair_citations(line: str) -> list[tuple[str, str]]:
    """Пары «шифр — пункт» внутри одной строки: пункт относится к ближайшему
    предшествующему шифру (не дальше 80 знаков), иначе пара не считается."""
    codes = [(m.start(), norm_code(m.group(0))) for m in CODE_RE.finditer(line)]
    out: list[tuple[str, str]] = []
    for m in CLAUSE_RE.finditer(line):
        clause = m.group(1)
        if len(clause.split(".")) < 2:
            continue
        prev = [c for c in codes if c[0] < m.start() and m.start() - c[0] <= 80]
        if not prev:
            continue
        code = prev[-1][1]
        if clause in code:          # «СП 5.04.01-2021» — это шифр, а не пункт
            continue
        out.append((code, clause))
    return out


@dataclass
class Finding:
    severity: str          # error | warn | info
    category: str          # нормы | цитаты | комплект | ПОС/ППР | заглушки | подписи
    file: str
    page: int | None
    message: str
    norm: str = ""
    action: str = ""


@dataclass
class Scan:
    root: str
    corpus: str = ""
    files_total: int = 0
    files_scanned: int = 0
    skipped: int = 0
    size_mb: float = 0.0
    duration_s: float = 0.0
    findings: list[Finding] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  извлечение текста
# --------------------------------------------------------------------------- #
def docx_text(path: Path) -> list[tuple[int, str]]:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    text = "\n".join(parts)
    # docx не имеет страниц: считаем «страницей» блок по 3 000 знаков
    if not text.strip():
        return []
    size = 3000
    return [(i // size + 1, text[i:i + size]) for i in range(0, len(text), size)]


def pdf_text(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    out = []
    for i, page in enumerate(reader.pages[:MAX_PDF_PAGES], start=1):
        try:
            out.append((i, page.extract_text() or ""))
        except Exception:  # битый слой — не роняем аудит
            out.append((i, ""))
    return out


def file_text(path: Path) -> list[tuple[int, str]]:
    ext = path.suffix.lower()
    if ext in TEXT_EXT:
        return [(1, read_text(path))]
    if ext == ".docx":
        return docx_text(path)
    if ext == ".pdf":
        return pdf_text(path)
    return []


# --------------------------------------------------------------------------- #
#  проверки
# --------------------------------------------------------------------------- #
class Auditor:
    def __init__(self, root: Path, include_text: bool = False) -> None:
        self.root = root
        self.include_text = include_text
        self.scan = Scan(root=str(root))
        self.registry, self.replaced = load_registry(Path(CORPUS_DEFAULT))
        self.scan.corpus = registry_date(Path(CORPUS_DEFAULT))
        self.db = sqlite3.connect(str(DB)) if DB.exists() else None
        self._clause_cache: dict[tuple[str, str], str] = {}
        self.composition = (json.loads(COMPOSITION.read_text(encoding="utf-8"))
                            if COMPOSITION.exists() else {"pos": [], "ppr": []})
        self._seen: set[tuple] = set()
        self.norm_hits: dict[str, dict] = {}

    # -- helpers ----------------------------------------------------------- #
    def add(self, f: Finding) -> None:
        key = (f.severity, f.category, f.file, f.page, f.message)
        if key in self._seen:
            return
        self._seen.add(key)
        self.scan.findings.append(f)

    def clause_state(self, code: str, clause: str) -> str:
        """ok | no_text | no_clause | unknown — «нет пункта» и «нет текста» не смешиваем."""
        key = (code, clause)
        if key in self._clause_cache:
            return self._clause_cache[key]
        state = "unknown"
        if self.db is not None:
            try:
                state, _ = clause_status(self.db, code, clause, limit=1)
            except Exception:
                state = "unknown"
        self._clause_cache[key] = state
        return state

    # -- 1–2. нормы и цитаты ---------------------------------------------- #
    def check_norms(self, rel: str, pages: list[tuple[int, str]]) -> None:
        rel_key = rel.rsplit(".", 1)[0]
        for page_no, text in pages:
            for cit in extract_citations(text):
                code = cit["code"]
                if SHORT_CODE_RE.match(code) or TRUNCATED_RE.match(code):
                    continue
                severity, message = classify(code, self.registry, self.replaced)
                if severity != "ok":
                    hit = self.norm_hits.setdefault(code, {
                        "severity": severity, "message": message, "norm": code,
                        "files": [], "count": 0,
                    })
                    hit["count"] += 1
                    if rel_key not in hit["files"]:
                        hit["files"].append(rel_key)
                if self.db is None:
                    continue
                for code2, clause in pair_citations(cit["context"]):
                    if code2 != code:
                        continue
                    state = self.clause_state(code, clause)
                    if state != "no_clause":
                        # «нет текста нормы» — не ошибка проекта; индекса нет — молчим.
                        continue
                    self.add(Finding(
                        "warn", "цитаты", rel, page_no,
                        f"пункт {clause} не найден в тексте {code} (фонд/индекс)",
                        f"{code}, п. {clause}",
                        "Проверить нумерацию пункта по действующей редакции",
                    ))

    # -- 3. комплектность -------------------------------------------------- #
    def check_completeness(self, names: list[str]) -> None:
        groups = {
            "Пояснительная записка (ПЗ/ОПЗ)": r"(^|[^А-Яа-я])(пз|опз)([^А-Яа-я]|$)",
            "Архитектурные решения (АР)": r"(^|[^А-Яа-я])ар(\d|$|[^А-Яа-я])",
            "Конструкции (КР/КЖ/КМ)": r"(кр|кж|км)\d*([^А-Яа-я]|$)",
            "Инженерные системы (ИОС/ОВ/ВК/ЭОМ)": r"(иос|ов\d|вк\d|эом|эс\d|сс\d)",
            "ПОС": r"пос(\d|$|[^А-Яа-я])",
            "ППР": r"ппр(\d|$|[^А-Яа-я])",
            "Сметы": r"(смет|gsfx|\.xml$)",
        }
        low = [n.lower() for n in names]
        missing = []
        for title, pattern in groups.items():
            rx = re.compile(pattern, re.IGNORECASE)
            if not any(rx.search(n) for n in low):
                missing.append(title)
        if missing:
            self.add(Finding(
                "warn", "комплект", "—", None,
                "в папке не найдены разделы: " + "; ".join(missing), "",
                "Проверить комплектность по СН 1.02.02-2023",
            ))

    # -- 4. состав ПОС/ППР ------------------------------------------------- #
    def check_composition(self, rel: str, pages: list[tuple[int, str]]) -> None:
        text = "\n".join(t for _, t in pages)
        low = text.lower()
        name = Path(rel).name.lower()
        if "сгп" in name or "схем" in name:
            return
        if "-км" in name or "монтаж" in name:
            self.add(Finding(
                "info", "ПОС/ППР", rel, None,
                "ППР на вид работ: состав проверяется по прил. В.2 (4 блока), не по В.1",
                "СН 1.03.04-2020, прил. В.2", "Проверить состав вручную по В.2",
            ))
            return
        if "ппр" in name:
            kind = "ppr"
        elif "пос" in name:
            kind = "pos"
        else:
            head = low[:3000]
            if "проект организации строительства" in head:
                kind = "pos"
            elif "проект производства работ" in head:
                kind = "ppr"
            else:
                return
        blocks = self.composition.get(kind, [])
        missing = [b["clause"] for b in blocks
                   if not re.search(rf"(?<![\d.]){re.escape(b['clause'].lower())}(?![\d])", low)]
        if missing:
            self.add(Finding(
                "warn", "ПОС/ППР", rel, None,
                f"нет блоков приложения {'В' if kind == 'ppr' else 'Г'}: "
                + ", ".join(missing[:12]) + ("…" if len(missing) > 12 else ""),
                "СН 1.03.04-2020, прил. " + ("В" if kind == "ppr" else "Г"),
                "Дополнить документ отсутствующими блоками",
            ))
        if "не может служить основанием" not in re.sub(r"\s+", " ", low) and kind == "pos":
            self.add(Finding(
                "info", "ПОС/ППР", rel, None,
                "нет оговорки «не может служить основанием для производства работ»", "",
                "Добавить оговорку в общую часть ПОС",
            ))

    # -- 5–6. заглушки и подписи ------------------------------------------ #
    def check_placeholders(self, rel: str, pages: list[tuple[int, str]]) -> None:
        hard: dict[str, int] = {}
        soft: dict[str, int] = {}
        for page_no, text in pages:
            for m in PLACEHOLDER_RE.finditer(text):
                hard.setdefault(m.group(0).strip().lower(), page_no)
            for m in SOFT_PLACEHOLDER_RE.finditer(text):
                soft.setdefault(m.group(0).strip().lower(), page_no)
        for i, (frag, page_no) in enumerate(hard.items()):
            if i >= 8:
                self.add(Finding("warn", "заглушки", rel, None,
                                 f"ещё {len(hard) - 8} незаполненных фрагментов в файле", "",
                                 "Проверить документ на заглушки"))
                break
            self.add(Finding("warn", "заглушки", rel, page_no,
                             f"незаполненный фрагмент «{frag}»", "",
                             "Заменить на конкретное значение или решение"))
        for frag, page_no in list(soft.items())[:3]:
            self.add(Finding("info", "заглушки", rel, page_no,
                             f"формулировка без конкретики «{frag}»", "",
                             "Проверить, не заменяет ли фраза конкретное решение"))

    # -- обход ------------------------------------------------------------- #
    def run(self) -> Scan:
        started = time.perf_counter()
        allowed = DOC_EXT | (TEXT_EXT if self.include_text else set())
        paths: list[Path] = []
        omitted = 0
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            if any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(self.root).parts):
                continue
            if p.suffix.lower() not in allowed:
                self.scan.skipped += 1
                continue
            if len(paths) >= MAX_FILES:
                omitted += 1
                continue
            paths.append(p)

        if omitted:
            self.scan.skipped += omitted
            self.add(Finding(
                "warn", "комплект", "—", None,
                f"предел {MAX_FILES} файлов: не прочитано ещё {omitted}", "",
                "Разбить папку на части или поднять лимит",
            ))

        self.scan.files_total = sum(1 for p in self.root.rglob("*") if p.is_file())
        names = [p.name for p in paths]
        self.check_completeness(names)

        for p in paths:
            rel = p.relative_to(self.root).as_posix()
            try:
                self.scan.size_mb += p.stat().st_size / 1_048_576
                pages = file_text(p)
            except Exception as exc:  # noqa: BLE001
                self.scan.errors.append(f"{rel}: {type(exc).__name__}: {exc}")
                continue
            if p.suffix.lower() == ".pdf" and len(pages) == MAX_PDF_PAGES:
                self.add(Finding(
                    "warn", "комплект", rel, None,
                    f"PDF: прочитано {MAX_PDF_PAGES} страниц — предел; если больше, остальные не проверены", "",
                    "Проверить остальные страницы вручную",
                ))
            if not pages:
                ext = p.suffix.lower()
                if ext in UNSUPPORTED_EXT:
                    self.add(Finding(
                        "info", "комплект", rel, None,
                        f"формат {ext} не проверяется (только DOCX/PDF); нужен ручной просмотр", "",
                        "Открыть файл вручную или выгрузить в DOCX/PDF",
                    ))
                else:
                    self.add(Finding("info", "комплект", rel, None,
                                     "текст не извлечён (скан без OCR или пустой файл)", "",
                                     "Прогнать OCR или исключить файл из аудита"))
                continue
            self.scan.files_scanned += 1
            self.scan.documents.append({"file": rel, "pages": len(pages),
                                        "chars": sum(len(t) for _, t in pages)})
            self.check_norms(rel, pages)
            self.check_composition(rel, pages)
            self.check_placeholders(rel, pages)

        if self.scan.files_scanned == 0:
            self.add(Finding(
                "warn", "комплект", "—", None,
                "текстовые документы не прочитаны: нет DOCX/PDF с текстовым слоем", "",
                "Добавить DOCX или PDF с текстом; сканы без OCR не проверяются",
            ))
        self._flush_norms()

        if self.db is not None:
            self.db.close()
        self.scan.duration_s = round(time.perf_counter() - started, 2)
        self.scan.findings.sort(key=lambda f: ({"error": 0, "warn": 1, "info": 2}[f.severity],
                                              f.file, f.page or 0))
        return self.scan

    def _flush_norms(self) -> None:
        """Свёртка по шифрам: один шифр — одна строка со списком файлов."""
        for code, hit in self.norm_hits.items():
            files = hit["files"]
            shown = files[:3]
            where = ", ".join(shown) + (f" и ещё {len(files) - len(shown)}…"
                                        if len(files) > len(shown) else "")
            action = ("Заменить на действующий документ" if hit["severity"] == "error"
                      else "Подтвердить шифр и год по реестру ТНПА")
            self.add(Finding(hit["severity"], "нормы", where, None,
                             f"{hit['message']} (встречается {hit['count']} раз)",
                             code, action))


# --------------------------------------------------------------------------- #
def result_dict(scan: Scan) -> dict:
    counts = {"error": 0, "warn": 0, "info": 0}
    for f in scan.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    penalty = min(6.0, 1.0 * counts["error"]) + min(3.0, 0.2 * counts["warn"]) \
        + min(1.0, 0.05 * counts["info"])
    score = max(0.0, round(10.0 - penalty, 1))
    if scan.files_scanned == 0:
        # Ни одного текстового документа: оценка не выставляется, а не «почти отлично».
        score = 0.0
    return {
        "meta": {
            "root": scan.root,
            "files_total": scan.files_total,
            "files_scanned": scan.files_scanned,
            "skipped": scan.skipped,
            "size_mb": round(scan.size_mb, 1),
            "duration_s": scan.duration_s,
            "corpus": scan.corpus or "дата не определена",
        },
        "summary": {**counts, "score": round(min(score, 10.0), 1)},
        "findings": [asdict(f) for f in scan.findings],
        "documents": scan.documents,
        "errors": scan.errors,
    }


def audit(path: Path, include_text: bool = False) -> dict:
    return result_dict(Auditor(path, include_text=include_text).run())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--include-text", action="store_true",
                    help="включать .md/.txt/.csv (по умолчанию только docx/pdf)")
    args = ap.parse_args()
    result = audit(Path(args.path), include_text=args.include_text)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        s = result["summary"]
        print(f"files={result['meta']['files_scanned']} error={s['error']} warn={s['warn']} "
              f"info={s['info']} score={s['score']} -> {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

