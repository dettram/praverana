"""Каких норм реестра нет в корпусе файлом — и насколько часто на них ссылаются проекты.

  uv run scripts/pdf_gaps.py --out gaps.csv --top 40
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CODE_RE, CORPUS_DEFAULT, clean, extract_citations, norm_code, year_of  # noqa: E402


def norm_key(text: str) -> str:
    return re.sub(r"[^0-9A-ZА-ЯЁ]", "", (text or "").upper())


def registry_codes(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            raw = (row.get("Шифр") or "").strip()
            if not CODE_RE.search(raw):
                continue
            code = norm_code(raw)
            if year_of(code) is None:
                continue
            out.setdefault(code, row)
    return out


def corpus_files(corpus: Path) -> list[tuple[str, Path]]:
    items = []
    for p in corpus.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".txt", ".md"):
            items.append((norm_key(p.name), p))
    return items


def citation_counts(corpus: Path) -> Counter:
    counts: Counter = Counter()
    root = corpus / "04-Аудиты"
    if not root.exists():
        return counts
    for f in root.rglob("*"):
        if f.suffix.lower() not in (".md", ".txt") or not f.is_file() or f.stat().st_size > 500_000:
            continue
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if len(line) > 5000:
                continue
            for cit in extract_citations(line):
                counts[cit["code"]] += 1
    return counts


def index_codes(db_path: Path) -> set[str]:
    """Коды, реально встречающиеся в текстах норм (а не только в проектных ссылках)."""
    import sqlite3

    if not db_path.exists():
        return set()
    db = sqlite3.connect(db_path)
    found: set[str] = set()
    sql = """
      SELECT c.text FROM chunks c JOIN docs d ON d.id = c.doc_id
      WHERE d.status = 'ok'
        AND (d.rel LIKE '05-%' OR d.rel LIKE '06-%' OR d.rel LIKE '03-%' OR d.rel LIKE '_inbox-%')
        AND c.page <= 5
    """
    for (text,) in db.execute(sql):
        for m in CODE_RE.finditer(clean(text)):
            found.add(norm_code(m.group(0)))
    db.close()
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--index", default=str(Path.home() / ".stroy-audit" / "index.sqlite"))
    ap.add_argument("--out", default="")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--active-only", action="store_true")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    reg = registry_codes(corpus / "02-Реестр.csv")
    files = corpus_files(corpus)
    cites = citation_counts(corpus)

    manifested = set()
    for m in corpus.glob("_inbox-*/manifest.csv"):
        with m.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh, delimiter=";"):
                if (row.get("code") or "").strip():
                    manifested.add(norm_code(row["code"]))
    in_text = index_codes(Path(args.index))

    gaps = []
    for code, row in reg.items():
        key = norm_key(code)
        if not key or code in manifested or code in in_text:
            continue
        hits = [str(p.relative_to(corpus)) for k, p in files if key in k]
        if hits:
            continue
        gaps.append({
            "code": code,
            "vid": row.get("Вид", ""),
            "name": row.get("Наименование", ""),
            "status": row.get("Статус на 18.11.2026", ""),
            "citations": cites.get(code, 0),
        })
    gaps.sort(key=lambda g: (-g["citations"], g["vid"], g["code"]))
    if args.active_only:
        gaps = [g for g in gaps if (g["status"] or "").startswith("действ")]

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["code", "vid", "name", "status", "citations"], delimiter=";")
            w.writeheader()
            w.writerows(gaps)
        print(f"written: {out} ({len(gaps)} gaps)")
    for g in gaps[: args.top]:
        print(f"{g['citations']:>3}  {g['code']:<24} {g['vid']:<4} {(g['name'] or '')[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
