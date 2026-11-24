"""Регрессионные тесты базы: индекс, пункты, статусы, поиск, цитаты.

  uv run --with snowballstemmer scripts/check_all.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clause import find_clause  # noqa: E402
from common import CORPUS_DEFAULT  # noqa: E402
from norm_check import classify, load_registry  # noqa: E402
from search import fts_query, stem_query  # noqa: E402

DB = Path.home() / ".stroy-audit" / "index.sqlite"
FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def main() -> int:
    db = sqlite3.connect(DB)

    docs = db.execute("SELECT COUNT(*), COALESCE(SUM(pages),0) FROM docs WHERE status='ok'").fetchone()
    clauses = db.execute("SELECT COUNT(*) FROM clauses").fetchone()[0]
    stems = db.execute("SELECT COUNT(*) FROM chunks_stem").fetchone()[0]
    check("index docs >= 400", docs[0] >= 400, f"{docs[0]}")
    check("index pages >= 12000", docs[1] >= 12000, f"{docs[1]}")
    check("clauses >= 40000", clauses >= 40000, f"{clauses}")
    check("stems >= 60000", stems >= 60000, f"{stems}")

    golden = [
        ("СП 5.03.01-2020", "6.3.4.1", True),
        ("СН 2.01.04-2025", "5.1", True),
        ("СП 5.03.01-2020", "99.99.99", False),
    ]
    for code, clause, want in golden:
        hits = find_clause(db, code, clause)
        check(f"clause {code} п.{clause}", bool(hits) == want,
              f"{hits[0]['file']}:{hits[0]['page']}" if hits else "не найдено")

    registry, replaced = load_registry(Path(CORPUS_DEFAULT))
    cases = [
        ("СП 5.03.01-2020", "ok"),
        ("ТКП 339-2011", "error"),
        ("СНиП II-23-81", "error"),
        ("СН 9.99.99-2020", "warn"),
    ]
    for code, want in cases:
        got = classify(code, registry, replaced)[0]
        check(f"classify {code}", got == want, f"{got}")

    searches = [
        ("защитный слой бетона", "5.03.01"),
        ("снеговые нагрузки", "2.01.04"),
        ("прецизионные трубы", "9567"),
    ]
    for query, expect in searches:
        q = stem_query(query)
        table = "chunks_stem" if q and db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='chunks_stem'").fetchone() else None
        if table:
            rows = db.execute(
                f"SELECT d.rel FROM {table} JOIN chunks c ON c.id={table}.rowid "
                f"JOIN docs d ON d.id=c.doc_id WHERE {table} MATCH ? "
                f"AND (d.rel LIKE '01-%' OR d.rel LIKE '02-%') ORDER BY bm25(chunks_stem) LIMIT 50",
                [q],
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT d.rel FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid "
                "JOIN docs d ON d.id=c.doc_id WHERE chunks_fts MATCH ? "
                "AND (d.rel LIKE '01-%' OR d.rel LIKE '02-%') ORDER BY bm25(chunks_fts) LIMIT 50",
                [fts_query(query)],
            ).fetchall()
        check(f"search «{query}»", any(expect in r[0] for r in rows), f"{len(rows)} hits")

    db.close()
    if FAILED:
        print(f"\nПРОВАЛЕНО: {len(FAILED)}")
        return 1
    print("\nВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


