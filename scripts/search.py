"""Поиск по индексу корпуса: пункт нормы → файл:страница + фрагмент.

  uv run scripts/search.py --query "защитный слой" --code "СП 5.03.01-2020"
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".stroy-audit" / "index.sqlite"


def fts_query(text: str) -> str:
    tokens = re.findall(r"[\wА-Яа-яЁё]+", text, re.UNICODE)
    return " ".join(f'"{t}"*' for t in tokens if len(t) > 1)


def make_snippet(text: str, query: str, width: int = 160) -> str:
    low = text.lower()
    best = None
    for tok in re.findall(r"[\wА-Яа-яЁё]+", query.lower()):
        pos = low.find(tok)
        if pos >= 0 and (best is None or pos < best):
            best = pos
    if best is None:
        return re.sub(r"\s+", " ", text[: width * 2]).strip()
    start = max(0, best - width)
    end = min(len(text), best + width)
    frag = re.sub(r"\s+", " ", text[start:end]).strip()
    return ("…" if start else "") + frag + ("…" if end < len(text) else "")


def stem_query(text: str) -> str | None:
    try:
        from snowballstemmer import stemmer
    except ImportError:
        return None
    st = stemmer("russian").stemWord
    tokens = re.findall(r"[\wА-Яа-яЁё]+", text, re.UNICODE)
    return " ".join(f'"{st(t.lower())}"' for t in tokens if len(t) > 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="")
    ap.add_argument("--query-file", default="", help="UTF-8 файл с запросом (для консолей с cp1251)")
    ap.add_argument("--code", default="", help="фильтр по шифру, например «СП 5.03.01-2020»")
    ap.add_argument("--path", default="", help="фильтр по части пути")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-stem", action="store_true", help="отключить морфологический поиск")
    ap.add_argument("--out", default="", help="писать результат в UTF-8 файл")
    args = ap.parse_args()
    query = args.query or ""
    if args.query_file:
        query = Path(args.query_file).read_text(encoding="utf-8").strip()
    if not query:
        print(json.dumps({"error": "empty query"}, ensure_ascii=False))
        return 2

    db_path = Path(args.db)
    if not db_path.exists():
        print(json.dumps({"error": "index not found", "hint": "run scripts/build_index.py"}, ensure_ascii=False))
        return 2

    where, params = [], []
    if args.code:
        where.append("d.code LIKE ?")
        params.append(f"%{args.code}%")
    if args.path:
        where.append("d.rel LIKE ?")
        params.append(f"%{args.path}%")
    clause = (" AND " + " AND ".join(where)) if where else ""

    sql = f"""
      SELECT d.rel, d.code, c.page,
             snippet(chunks_fts, 0, '[', ']', '…', 14) AS s,
             bm25(chunks_fts) AS score
      FROM chunks_fts
      JOIN chunks c ON c.id = chunks_fts.rowid
      JOIN docs d ON d.id = c.doc_id
      WHERE chunks_fts MATCH ? {clause}
      ORDER BY score
      LIMIT ?
    """
    db = sqlite3.connect(db_path)
    query_text = fts_query(query)
    use_stem = not args.no_stem
    stemmed = stem_query(query) if use_stem else None
    has_stem = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunks_stem'"
    ).fetchone() if stemmed else None

    if stemmed and has_stem:
        stem_sql = f"""
          SELECT d.rel, d.code, c.page, c.text, bm25(chunks_stem) AS score
          FROM chunks_stem
          JOIN chunks c ON c.id = chunks_stem.rowid
          JOIN docs d ON d.id = c.doc_id
          WHERE chunks_stem MATCH ? {clause}
          ORDER BY score
          LIMIT ?
        """
        try:
            rows = db.execute(stem_sql, [stemmed, *params, args.limit]).fetchall()
        except sqlite3.OperationalError as exc:
            print(json.dumps({"error": str(exc), "query": stemmed}, ensure_ascii=False))
            return 2
        items = [
            {"file": r[0], "code": r[1], "page": r[2],
             "snippet": make_snippet(r[3], query), "score": round(r[4], 4)}
            for r in rows
        ]
    else:
        try:
            rows = db.execute(sql, [query_text, *params, args.limit]).fetchall()
        except sqlite3.OperationalError as exc:
            print(json.dumps({"error": str(exc), "query": query_text}, ensure_ascii=False))
            return 2
        items = [
            {"file": r[0], "code": r[1], "page": r[2], "snippet": re.sub(r"\s+", " ", r[3]),
             "score": round(r[4], 4)}
            for r in rows
        ]
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0 if items else 1
    lines = []
    for it in items:
        lines.append(f"{it['file']}:{it['page']}  [{it['code'] or '—'}]")
        lines.append(f"   {it['snippet']}\n")
    if not items:
        lines.append("Ничего не найдено. Проверь шифр/формулировку или пересобери индекс.")
    text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"written: {args.out}")
    else:
        print(text)
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(main())
