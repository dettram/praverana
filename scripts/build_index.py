"""Индексация нормативного корпуса в SQLite + FTS5.

Индексируются текст, PDF (текстовый слой), DOCX, XLSX. Сканы без текста попадают
в отчёт как no_text — молча пропускать нельзя: на них потом ссылаются как на «норму».

  uv run --with pypdf --with python-docx --with openpyxl scripts/build_index.py
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, SUPPORTED, ensure_dir, norm_code, CODE_RE, pages_of  # noqa: E402

DEFAULT_OUT = Path.home() / ".stroy-audit" / "index.sqlite"
DEFAULT_SKIP = (
    "03-Серии",
    "05-BIM",
    "06-Справочники/Карточки-изделий/OCR",
    "_архив",
    ".git",
    ".serena",
    "node_modules",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(
  id INTEGER PRIMARY KEY,
  rel TEXT UNIQUE,
  title TEXT,
  code TEXT,
  kind TEXT,
  pages INTEGER,
  chars INTEGER,
  status TEXT,
  detail TEXT
);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY,
  doc_id INTEGER NOT NULL,
  page INTEGER,
  ord INTEGER,
  text TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text, content='chunks', content_rowid='id', tokenize='unicode61'
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
"""


def chunk_text(pages: list[str], target: int = 1200, overlap: int = 150) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for pno, page in enumerate(pages, 1):
        page = page.strip()
        if not page:
            continue
        paras = [p.strip() for p in re.split(r"\n\s*\n|\n(?=#)", page) if p.strip()]
        buf = ""
        for para in paras:
            if len(buf) + len(para) + 1 <= target:
                buf = f"{buf}\n{para}" if buf else para
                continue
            if buf:
                out.append((pno, 0, buf))
                buf = buf[-overlap:] if overlap else ""
            while len(para) > target:
                out.append((pno, 0, para[:target]))
                para = para[target - overlap:]
            buf = f"{buf}\n{para}".strip() if buf else para
        if buf.strip():
            out.append((pno, 0, buf.strip()))
    for i, (pno, _, text) in enumerate(out):
        out[i] = (pno, i, text)
    return out


def code_of(name: str) -> str:
    m = CODE_RE.search(name)
    return norm_code(m.group(0)) if m else ""


def iter_files(corpus: Path, skips: tuple[str, ...]):
    for path in sorted(corpus.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        rel = path.relative_to(corpus).as_posix()
        if any(sk in rel for sk in skips):
            continue
        yield path, rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max-mb", type=float, default=40.0)
    ap.add_argument("--skip", default=",".join(DEFAULT_SKIP))
    ap.add_argument("--limit", type=int, default=0, help="0 = все файлы")
    ap.add_argument("--only", default="", help="подстрока пути: индексировать только совпавшие файлы")
    ap.add_argument("--append", action="store_true", help="дописать в существующую БД, пропуская уже indexed")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    if not corpus.exists():
        print(json.dumps({"error": f"corpus not found: {corpus}"}, ensure_ascii=False))
        return 2

    out = ensure_dir(Path(args.out).parent) / Path(args.out).name
    if out.exists() and not args.append:
        out.unlink()

    skips = tuple(s for s in args.skip.split(",") if s)
    db = sqlite3.connect(out)
    db.executescript(SCHEMA)
    existing = {row[0] for row in db.execute("SELECT rel FROM docs")} if args.append else set()
    stats = {"docs": 0, "pages": 0, "chunks": 0, "no_text": [], "locked": [], "errors": [], "skipped_big": []}
    started = time.time()

    files = list(iter_files(corpus, skips))
    if args.limit:
        files = files[: args.limit]

    for path, rel in files:
        if args.only and args.only.lower() not in rel.lower():
            continue
        if rel in existing:
            continue
        try:
            size_mb = path.stat().st_size / 1048576
        except FileNotFoundError:
            continue
        if size_mb > args.max_mb:
            stats["skipped_big"].append({"rel": rel, "mb": round(size_mb, 1)})
            continue
        try:
            pages = pages_of(path)
        except Exception as exc:  # noqa: BLE001
            name = type(exc).__name__
            locked = "Decrypt" in name or "Password" in name
            stats["locked" if locked else "errors"].append({"rel": rel, "error": f"{name}: {exc}"})
            db.execute(
                "INSERT INTO docs(rel,title,code,kind,pages,chars,status,detail) VALUES(?,?,?,?,?,?,?,?)",
                (rel, path.stem, code_of(path.stem), path.suffix.lower(), 0, 0,
                 "locked" if locked else "error", f"{name}: {exc}"),
            )
            db.commit()
            continue

        chars = sum(len(p) for p in pages)
        status = "ok" if chars >= 200 else "no_text"
        title = path.stem
        code = code_of(title)
        cur = db.execute(
            "INSERT INTO docs(rel,title,code,kind,pages,chars,status,detail) VALUES(?,?,?,?,?,?,?,?)",
            (rel, title, code, path.suffix.lower(), len(pages), chars, status,
             "" if status == "ok" else "текстовый слой отсутствует или короче 200 символов"),
        )
        doc_id = cur.lastrowid
        if status != "ok":
            stats["no_text"].append(rel)
            db.commit()
            continue

        rows = [(doc_id, pno, ord_, text) for pno, ord_, text in chunk_text(pages)]
        db.executemany("INSERT INTO chunks(doc_id,page,ord,text) VALUES(?,?,?,?)", rows)
        db.executemany(
            "INSERT INTO chunks_fts(rowid,text) SELECT id,text FROM chunks WHERE doc_id=?",
            [(doc_id,)],
        )
        stats["docs"] += 1
        stats["pages"] += len(pages)
        stats["chunks"] += len(rows)
        if stats["docs"] % 20 == 0:
            print(f"… {stats['docs']} docs", file=sys.stderr)
        db.commit()

    db.commit()
    db.close()
    stats["seconds"] = round(time.time() - started, 1)
    stats["db"] = str(out)
    stats["db_mb"] = round(out.stat().st_size / 1048576, 1) if out.exists() else 0
    stats["files_seen"] = len(files)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
