"""Проверка пункта нормы по индексу корпуса: существует ли пункт и на какой странице.

  uv run scripts/clause.py --code "СП 5.03.01-2020" --clause 6.3.4.1
  uv run scripts/clause.py --text ".\объект\ПЗ.md"

Различает три состояния: пункт найден (`ok`), текста нормы нет в индексе (`no_text`),
текст есть, пункта нет (`no_clause`). Первое и второе нельзя смешивать: иначе движок
пишет «пункт не найден» для нормы, которой нет в фонде.
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


def codes_in(text: str) -> set[str]:
    """Все канонические шифры из строки (имя файла, колонка code)."""
    return {norm_code(m.group(0)) for m in CODE_RE.finditer(text or "")}


def docs_for_code(db: sqlite3.Connection, code: str) -> list[tuple[int, str]]:
    """Документы фонда с этим шифром. Сравнение по канону, без склейки СН и СП."""
    target = norm_code(code)
    if not target:
        return []
    out = []
    for doc_id, rel, dcode in db.execute("SELECT id, rel, code FROM docs WHERE status='ok'"):
        if target in (codes_in(dcode) | codes_in(rel)):
            out.append((doc_id, rel))
    return out


def _indexed_hits(db: sqlite3.Connection, code: str, clause: str, limit: int) -> list[dict]:
    try:
        rows = db.execute(
            """SELECT d.rel, c.page, c.title FROM clauses c JOIN docs d ON d.id = c.doc_id
               WHERE c.code=? AND c.clause=? LIMIT ?""",
            (code, clause, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [{"file": r[0], "page": r[1], "snippet": f"{clause} — {r[2]}"} for r in rows]


def clause_status(db: sqlite3.Connection, code: str, clause: str,
                  limit: int = 3) -> tuple[str, list[dict]]:
    """('ok' | 'no_text' | 'no_clause', hits)."""
    hits = _indexed_hits(db, code, clause, limit)
    if hits:
        return "ok", hits

    docs = docs_for_code(db, code)
    if not docs:
        return "no_text", []

    pattern = re.compile(rf"(?<![\d.]){re.escape(clause)}(?![\d])", re.IGNORECASE)
    found: list[dict] = []
    chunks = 0
    for doc_id, rel in docs:
        rows = db.execute("SELECT page, text FROM chunks WHERE doc_id=?", (doc_id,)).fetchall()
        chunks += len(rows)
        for page, text in rows:
            m = pattern.search(text)
            if not m:
                continue
            start = max(0, m.start() - 80)
            snippet = re.sub(r"\s+", " ", text[start:m.end() + 160]).strip()
            found.append({"file": rel, "page": page, "snippet": snippet})
            break
        if len(found) >= limit:
            break
    if found:
        return "ok", found
    return ("no_text" if chunks == 0 else "no_clause"), []


def find_clause(db: sqlite3.Connection, code: str, clause: str, limit: int = 3) -> list[dict]:
    state, hits = clause_status(db, code, clause, limit)
    return hits if state == "ok" else []


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
            state, hits = clause_status(db, cit["code"], cit["clause"])
            results.append({**cit, "state": state, "found": state == "ok", "hits": hits})
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                label = {"ok": "OK ", "no_text": "НЕТ ТЕКСТА", "no_clause": "НЕТ ПУНКТА"}[r["state"]]
                where = f"{r['hits'][0]['file']}:{r['hits'][0]['page']}" if r["found"] else ""
                print(f"{label} {r['code']} {r['kind']} {r['clause']} — {where}".rstrip(" —"))
        return 0 if all(r["found"] for r in results) else 1

    if not args.code or not args.clause:
        print(json.dumps({"error": "need --code/--clause or --text"}, ensure_ascii=False))
        return 2
    state, hits = clause_status(db, norm_code(args.code), args.clause)
    if args.json:
        print(json.dumps({"state": state, "hits": hits}, ensure_ascii=False, indent=2))
    else:
        for h in hits:
            print(f"{h['file']}:{h['page']}\n   {h['snippet']}\n")
        if state == "no_text":
            print("Текста этой нормы нет в проиндексированном фонде — пункт не проверялся.")
        elif state == "no_clause":
            print("Пункта нет в проиндексированном тексте этой нормы.")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
