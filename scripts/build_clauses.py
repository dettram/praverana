"""Индекс пунктов: норма → пункт → заголовок → страница.

  uv run scripts/build_clauses.py
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".stroy-audit" / "index.sqlite"
CLAUSE_RE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,3}){0,4}[а-яё]?)\s*[.)]?\s+([А-ЯЁA-Z][^\n]{3,100})")
TABLE_RE = re.compile(
    r"^\s*(Таблица|Приложение)\s+"
    r"([А-ЯЁA-Z](?:\.\d{1,2})?|\d{1,2}(?:\.\d{1,3})*)\b\.?\s*[—\-:]?\s*([^\n]{0,90})",
    re.IGNORECASE,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()
    db_path = Path(args.db)
    db = sqlite3.connect(db_path)
    db.executescript("""
      DROP TABLE IF EXISTS clauses;
      CREATE TABLE clauses(
        id INTEGER PRIMARY KEY,
        doc_id INTEGER, code TEXT, clause TEXT, title TEXT, page INTEGER
      );
      CREATE INDEX idx_clauses_code ON clauses(code, clause);
    """)

    seen = set()
    rows = []
    sql = """
      SELECT c.doc_id, d.code, c.page, c.text
      FROM chunks c JOIN docs d ON d.id = c.doc_id
      WHERE d.status='ok'
    """
    for doc_id, code, page, text in db.execute(sql):
        for line in text.splitlines():
            line = line.strip()
            if not line or len(line) < 6:
                continue
            m = CLAUSE_RE.match(line)
            if m:
                clause = m.group(1).lower()
                title = re.sub(r"\s+", " ", m.group(2)).strip(" .—-")
                key = (doc_id, clause)
                if key in seen or not title:
                    continue
                seen.add(key)
                rows.append((doc_id, code or "", clause, title[:120], page))
                continue
            t = TABLE_RE.match(line)
            if t:
                kind, num, title = t.group(1).capitalize(), t.group(2), t.group(3).strip(" .—-")
                clause = f"{kind} {num.upper() if kind == 'Приложение' else num}"
                key = (doc_id, clause)
                if key in seen:
                    continue
                seen.add(key)
                rows.append((doc_id, code or "", clause, title[:120], page))

    db.executemany("INSERT INTO clauses(doc_id,code,clause,title,page) VALUES(?,?,?,?,?)", rows)
    db.commit()
    total = db.execute("SELECT COUNT(*) FROM clauses").fetchone()[0]
    docs = db.execute("SELECT COUNT(DISTINCT doc_id) FROM clauses").fetchone()[0]
    db.close()
    print(f"clauses={total} docs={docs} db={db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
