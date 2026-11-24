"""Аудит цитат в отчётах: какие «шифр + пункт» не подтверждаются текстом корпуса.

  uv run scripts/cite_audit.py --out "…/_inbox-2026-11-23/cite-audit.md"
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clause import docs_for_code, find_clause, parse_citations  # noqa: E402
from common import CORPUS_DEFAULT  # noqa: E402

DEFAULT_DB = Path.home() / ".stroy-audit" / "index.sqlite"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--out", default="")
    ap.add_argument("--max-mb", type=float, default=1.0)
    args = ap.parse_args()

    corpus = Path(args.corpus)
    db = sqlite3.connect(args.db)
    root = corpus / "04-Аудиты"

    reports = []
    for f in sorted(root.rglob("*.md")):
        if f.stat().st_size > args.max_mb * 1048576:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        cits = parse_citations(text)
        if not cits:
            continue
        rows = []
        for c in cits:
            hits = find_clause(db, c["code"], c["clause"], limit=1)
            has_text = bool(docs_for_code(db, c["code"]))
            status = "ok" if hits else ("no_text" if not has_text else "no_clause")
            rows.append({**c, "found": bool(hits), "status": status,
                         "where": f"{hits[0]['file']}:{hits[0]['page']}" if hits else ""})
        reports.append({"file": str(f.relative_to(corpus)), "rows": rows})

    total = sum(len(r["rows"]) for r in reports)
    ok = sum(1 for r in reports for x in r["rows"] if x["found"])
    missing = total - ok

    lines = [
        "# Аудит цитат в отчётах",
        "",
        f"Отчётов с цитатами: {len(reports)}; цитат: {total}; подтверждено: {ok}; не найдено: {missing}.",
        "",
    ]
    if missing:
        lines += ["## Не подтверждено", "",
                  "| Отчёт | Шифр | Пункт | Причина |", "|---|---|---|---|"]
        for r in reports:
            for x in r["rows"]:
                if not x["found"]:
                    reason = "нет текста нормы в корпусе" if x["status"] == "no_text" else "пункта нет в тексте нормы"
                    lines.append(f"| {Path(r['file']).parent.name} | {x['code']} | {x['kind']} {x['clause']} | {reason} |")
    else:
        lines.append("Все цитаты с пунктами подтверждены текстом корпуса.")

    top = Counter(f"{x['code']} {x['clause']}" for r in reports for x in r["rows"] if not x["found"])
    if top:
        lines += ["", "## Чаще всего не подтверждается", ""]
        lines += [f"- {k} — {v}" for k, v in top.most_common(10)]

    text = "\n".join(lines) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"written: {out} ({total} citations, {missing} missing)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
