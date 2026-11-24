"""Стеммированный FTS-индекс для морфологии (snowball, russian).

  uv run --with snowballstemmer scripts/build_stems.py
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".stroy-audit" / "index.sqlite"
TOKEN = re.compile(r"[\wА-Яа-яЁё]+", re.UNICODE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()

    from snowballstemmer import stemmer

    stem = stemmer("russian").stemWord
    db = sqlite3.connect(args.db)
    db.executescript("""
      DROP TABLE IF EXISTS chunks_stem;
      CREATE VIRTUAL TABLE chunks_stem USING fts5(text, tokenize='unicode61');
    """)

    batch = []
    count = 0
    for chunk_id, text in db.execute("SELECT id, text FROM chunks"):
        words = [stem(w.lower()) for w in TOKEN.findall(text)]
        batch.append((chunk_id, " ".join(words)))
        count += 1
        if len(batch) >= 2000:
            db.executemany("INSERT INTO chunks_stem(rowid, text) VALUES(?,?)", batch)
            batch.clear()
    if batch:
        db.executemany("INSERT INTO chunks_stem(rowid, text) VALUES(?,?)", batch)
    db.commit()
    print("stem chunks:", count)
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
