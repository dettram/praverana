"""Единый каталог корпуса: все файлы, шифры, дубли, покрытие текстом.

  uv run --with pypdf scripts/catalog_all.py
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CODE_RE, CORPUS_DEFAULT, norm_code, year_of  # noqa: E402

DEFAULT_DB = Path.home() / ".stroy-audit" / "index.sqlite"
SUFFIXES = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".csv", ".rvt", ".ifc",
            ".rar", ".zip", ".png", ".ids", ".rte", ".log"}
SERIES_RE = re.compile(r"Серия\s*([0-9][0-9.\-/]*)", re.IGNORECASE)
EN_RE = re.compile(r"\bEN\s*(\d{4}(?:-\d+)*)", re.IGNORECASE)


def detect_code(name: str) -> tuple[str, str]:
    m = CODE_RE.search(name)
    if m:
        code = norm_code(m.group(0))
        return code, code.split()[0]
    s = SERIES_RE.search(name)
    if s:
        return f"Серия {s.group(1).rstrip('-/')}", "Серия"
    e = EN_RE.search(name)
    if e:
        return f"EN {e.group(1)}", "EN"
    return "", "Прочее"


def index_status(db_path: Path) -> dict[str, str]:
    if not db_path.exists():
        return {}
    db = sqlite3.connect(db_path)
    out = {rel: status for rel, status in db.execute("SELECT rel, status FROM docs")}
    db.close()
    return out


def pages_of(path: Path) -> int:
    if path.suffix.lower() != ".pdf":
        return 0
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()

    corpus = Path(args.corpus)
    out_dir = corpus / "00-Каталог"
    out_dir.mkdir(exist_ok=True)
    status = index_status(Path(args.db))

    rows = []
    for p in sorted(corpus.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in SUFFIXES:
            continue
        rel = p.relative_to(corpus).as_posix()
        if rel.startswith("00-Каталог/"):
            continue
        code, vid = detect_code(p.name)
        rows.append({
            "path": rel,
            "vid": vid,
            "code": code,
            "ext": p.suffix.lower(),
            "size_kb": round(p.stat().st_size / 1024),
            "pages": pages_of(p),
            "text": status.get(rel, ""),
        })

    with (out_dir / "catalog-all.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "vid", "code", "ext", "size_kb", "pages", "text"],
                           delimiter=";")
        w.writeheader()
        w.writerows(rows)

    by_code: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["code"] and r["vid"] in ("СН", "СП", "СТБ", "ГОСТ", "ТКП", "СНБ", "Серия"):
            if r["path"].lower().endswith(".ocr.txt") or r["path"].startswith("_архив/"):
                continue
            by_code[r["code"]].append(r)

    dup_lines = ["# Дубли по шифрам", ""]
    dups = {c: v for c, v in by_code.items() if len(v) > 1}
    format_pairs = sum(1 for v in dups.values() if len({i["ext"] for i in v}) > 1)
    dup_lines.append(f"Шифров с несколькими файлами: **{len(dups)}** из {len(by_code)}; "
                     f"из них формат-пары (PDF+DOCX или PDF+изменение): {format_pairs}.")
    dup_lines.append("")
    for code, items in sorted(dups.items()):
        names = " ".join(Path(i["path"]).stem.lower() for i in items)
        if len({i["ext"] for i in items}) > 1:
            kind = "формат-пара"
        elif "изменени" in names:
            kind = "комплект (документ + изменение)"
        else:
            kind = "копии"
        dup_lines.append(f"## {code} — {len(items)} файл(ов), {kind}")
        for it in items:
            dup_lines.append(f"- `{it['path']}` — {it['pages']} стр., {it['size_kb']} КБ, текст: {it['text'] or '—'}")
        dup_lines.append("")
    (out_dir / "duplicates.md").write_text("\n".join(dup_lines), encoding="utf-8")

    group_lines = ["# Нормы по шифрам", ""]
    for vid in ("СН", "СП", "СТБ", "ГОСТ", "ТКП", "СНБ", "Серия"):
        items = [(c, v) for c, v in sorted(by_code.items()) if v[0]["vid"] == vid]
        if not items:
            continue
        group_lines.append(f"## {vid} ({len(items)})")
        group_lines.append("")
        for code, v in items:
            main = max(v, key=lambda x: (x["text"] == "ok", x["pages"], x["size_kb"]))
            extra = f" (+{len(v) - 1} копий)" if len(v) > 1 else ""
            group_lines.append(f"- **{code}** — `{main['path']}`{extra}")
        group_lines.append("")
    (out_dir / "by-code.md").write_text("\n".join(group_lines), encoding="utf-8")

    by_ext = Counter(r["ext"] for r in rows)
    no_text = [r for r in rows if r["ext"] == ".pdf" and r["text"] in ("no_text", "locked")]
    readme = [
        "# Каталог корпуса",
        "",
        f"Файлов: {len(rows)}; шифров: {len(by_code)}; групп с несколькими файлами: {len(dups)} "
        f"(формат-пар: {format_pairs}).",
        "",
        "По форматам: " + ", ".join(f"{k}={v}" for k, v in by_ext.most_common()),
        "",
        f"PDF без текстового слоя: {len(no_text)} (сканы/пароли) — по ним работает только просмотр.",
        "",
        "## Файлы",
        "",
        "- `catalog-all.csv` — все файлы: путь, вид, шифр, формат, размер, страницы, текстовый слой;",
        "- `by-code.md` — шифры по видам с основной копией;",
        "- `duplicates.md` — где одна норма лежит несколько раз.",
        "",
        "## Правила",
        "",
        "1. Основная копия — та, что с текстовым слоем и большим числом страниц.",
        "2. Дубли не удаляются: сначала проверка, потом решение.",
        "3. Файлы в `_inbox-*` — принятые позже, они приоритетнее старых копий при равном качестве.",
        "",
        "## Структура после раскладки",
        "",
        "`01-Нормы/СН|СП|СТБ|ГОСТ|ТКП|СНБ` — нормы; `02-Сортаменты`; `03-Серии`; `00-Каталог` — эта папка.",
        "Карта переносов — `moves.csv` (`from;to`), откат — обратный перенос.",
        "Пустая `06-Полные-тексты-WORD` удалена; `11-Серии-Металл-ЖБ` → `_архив`;",
        "`15-Сортаменты-и-стандарты` → `02-Сортаменты/_индекс`.",
    ]
    (out_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    print(f"files={len(rows)} codes={len(by_code)} dup_groups={len(dups)} no_text_pdf={len(no_text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
