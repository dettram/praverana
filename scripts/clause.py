"""Проверка пункта нормы по индексу корпуса: существует ли пункт и на какой странице.

  uv run scripts/clause.py --code "СП 5.03.01-2020" --clause 6.3.4.1
  uv run scripts/clause.py --text ".\объект\ПЗ.md"
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CODE_RE, extract_citations, norm_code  # noqa: E402

DEFAULT_DB = Path.home() / ".stroy-audit" / "index.sqlite"


def digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def docs_for_code(db: sqlite3.Connection, code: str) -> list[tuple[int, str]]:
    key = digits(code)
    out = []
    for doc_id, rel, dcode in db.execute("SELECT id, rel, code FROM docs WHERE status='ok'"):
        if key and (key in digits(rel) or key == digits(dcode)):
            out.append((doc_id, rel))
    return out


def find_clause(db: sqlite3.Connection, code: str, clause: str, limit: int = 3) -> list[dict]:
    indexed = []
    try:
        rows = db.execute(
            """SELECT d.rel, c.page, c.title FROM clauses c JOIN docs d ON d.id = c.doc_id
               WHERE c.code=? AND c.clause=? LIMIT ?""",
            (code, clause, limit),
        ).fetchall()
        indexed = [{"file": r[0], "page": r[1], "snippet": f"{clause} — {r[2]}"} for r in rows]
    except sqlite3.OperationalError:
        indexed = []
    if indexed:
        return indexed

    pattern = re.compile(rf"(?<![\d.]){re.escape(clause)}(?![\d])")
    hits = []
    for doc_id, rel in docs_for_code(db, code):
        rows = db.execute("SELECT page, text FROM chunks WHERE doc_id=?", (doc_id,)).fetchall()
        for page, text in rows:
            if pattern.search(text):
                m = pattern.search(text)
                start = max(0, m.start() - 80)
                snippet = re.sub(r"\s+", " ", text[start:m.end() + 160]).strip()
                hits.append({"file": rel, "page": page, "snippet": snippet})
                break
        if len(hits) >= limit:
            break
    return hits


def parse_citations(text: str) -> list[dict]:
    out = []
    for m in re.finditer(
        r"((?:СН|СП|СТБ|ГОСТ|ТКП)\s*\d+(?:[.\-]\d+)*-\d{4})\s*[,;:]?\s*"
        r"(п\.|пункт|табл\.|приложение|прил\.)\s*([\dА-ЯA-Z][\d.\-А-ЯA-Z]*)",
        text,
    ):
        out.append({"code": norm_code(m.group(1)), "kind": m.group(2), "clause": m.group(3).strip(" .")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="")
    ap.add_argument("--clause", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(json.dumps({"error": "index not found", "hint": "build_index.py"}, ensure_ascii=False))
        return 2
    db = sqlite3.connect(db_path)

    if args.text:
        text = Path(args.text).read_text(encoding="utf-8", errors="replace")
        results = []
        for cit in parse_citations(text):
            hits = find_clause(db, cit["code"], cit["clause"])
            results.append({**cit, "found": bool(hits), "hits": hits})
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                mark = "OK " if r["found"] else "НЕТ"
                where = f"{r['hits'][0]['file']}:{r['hits'][0]['page']}" if r["found"] else "не найдено в корпусе"
                print(f"{mark} {r['code']} {r['kind']} {r['clause']} — {where}")
        return 0 if all(r["found"] for r in results) else 1

    if not args.code or not args.clause:
        print(json.dumps({"error": "need --code/--clause or --text"}, ensure_ascii=False))
        return 2
    hits = find_clause(db, norm_code(args.code), args.clause)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    else:
        for h in hits:
            print(f"{h['file']}:{h['page']}\n   {h['snippet']}\n")
        if not hits:
            print("Не найдено: пункта нет в проиндексированном тексте этой нормы.")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
