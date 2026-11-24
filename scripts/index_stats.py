"""Сводка по индексу корпуса: что реально доступно текстом, а что скан.

  uv run scripts/index_stats.py
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

DEFAULT_DB = Path.home() / ".stroy-audit" / "index.sqlite"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(json.dumps({"error": "index not found", "hint": "build_index.py"}, ensure_ascii=False))
        return 2

    db = sqlite3.connect(db_path)
    docs = db.execute("SELECT status, kind, code FROM docs").fetchall()
    chunks = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    pages = db.execute("SELECT COALESCE(SUM(pages),0) FROM docs").fetchone()[0]
    no_text = [r[0] for r in db.execute("SELECT rel FROM docs WHERE status='no_text' ORDER BY rel").fetchall()]
    locked = [r[0] for r in db.execute("SELECT rel FROM docs WHERE status='locked' ORDER BY rel").fetchall()]

    top_codes = Counter(code for _, _, code in docs if code).most_common(15)
    stats = {
        "docs": len(docs),
        "ok": sum(1 for s, _, _ in docs if s == "ok"),
        "no_text": len(no_text),
        "locked": len(locked),
        "pages": pages,
        "chunks": chunks,
        "by_kind": dict(Counter(k for _, k, _ in docs)),
        "top_codes": top_codes,
        "db_mb": round(db_path.stat().st_size / 1048576, 1),
        "no_text_sample": no_text[:15],
    }
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print(f"Документов: {stats['docs']} (текстом {stats['ok']}, сканов {stats['no_text']}, закрытых паролем {stats['locked']})")
    print(f"Страниц: {stats['pages']}; фрагментов: {stats['chunks']}; БД: {stats['db_mb']} МБ")
    print("Типы:", ", ".join(f"{k}={v}" for k, v in stats["by_kind"].items()))
    print("Шифры в именах файлов:")
    for code, n in top_codes:
        print(f"  {code}: {n}")
    if no_text:
        print("Без текстового слоя (первые 15):")
        for rel in no_text[:15]:
            print("  -", rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
