"""Приём PDF нормы в корпус: проверка файла, раскладка, манифест, отметка в реестре.

  uv run --with pypdf scripts/ingest_pdf.py --file sn.pdf --code "СН 3.02.07-2020" `
      --title "Объекты строительства. Классификация" --source "https://…" --update-registry
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, norm_code  # noqa: E402

INBOX = "_inbox-2026-11-23"
MANIFEST = "manifest.csv"
COLUMNS = ["code", "file", "pages", "chars", "sha256", "source", "verdict", "checked"]


def digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def verify(path: Path, code: str) -> dict:
    head = path.read_bytes()[:5]
    if head != b"%PDF-":
        return {"verdict": "not_pdf", "pages": 0, "chars": 0, "note": head.decode("latin-1")}
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                pass
        pages = len(reader.pages)
        text = []
        for page in reader.pages[: min(pages, 200)]:
            try:
                text.append(page.extract_text() or "")
            except Exception:
                text.append("")
    except Exception as exc:  # noqa: BLE001
        return {"verdict": "unreadable", "pages": 0, "chars": 0, "note": f"{type(exc).__name__}: {exc}"}
    joined = "\n".join(text)
    chars = sum(len(t) for t in text)
    code_digits = digits(code)
    found = code_digits in digits(joined) if code_digits else False
    if chars < 200:
        verdict = "no_text"
    elif found:
        verdict = "verified"
    else:
        verdict = "mismatch"
    return {"verdict": verdict, "pages": pages, "chars": chars, "note": ""}


def process(src: Path, code_raw: str, title: str, source: str, corpus: Path, update_registry: bool) -> dict:
    code = norm_code(code_raw)
    vid = code.split()[0]
    folder = corpus / INBOX / vid
    folder.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r'[\\/:*?"<>|]', "-", title).strip()
    safe_code = re.sub(r'[\\/:*?"<>|]', "-", code).strip()
    dest = folder / f"{safe_code} — {safe_title}.pdf"
    shutil.copy2(src, dest)

    result = verify(dest, code)
    sha = hashlib.sha256(dest.read_bytes()).hexdigest()[:16]
    row = {
        "code": code,
        "file": str(dest.relative_to(corpus)),
        "pages": result["pages"],
        "chars": result["chars"],
        "sha256": sha,
        "source": source,
        "verdict": result["verdict"],
        "checked": date.today().isoformat(),
    }
    manifest = corpus / INBOX / MANIFEST
    exists = manifest.exists()
    with manifest.open("a", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter=";")
        if not exists:
            w.writeheader()
        w.writerow(row)

    if update_registry:
        reg = corpus / "02-Реестр.csv"
        rows = list(csv.DictReader(reg.open(encoding="utf-8-sig", newline=""), delimiter=";"))
        for r in rows:
            if norm_code(r.get("Шифр", "")) == code:
                src_note = (r.get("Источник") or "").strip()
                mark = f"PDF: {INBOX}/{vid}"
                if mark not in src_note:
                    r["Источник"] = f"{src_note}; {mark}" if src_note else mark
        with reg.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";", lineterminator="\r\n")
            w.writeheader()
            w.writerows(rows)

    return {"code": code, "file": row["file"], **result}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="")
    ap.add_argument("--code", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--spec", default="", help="JSON: [{file, code, title, source}]")
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--update-registry", action="store_true")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    items = []
    if args.spec:
        items = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    elif args.file and args.code:
        items = [{"file": args.file, "code": args.code, "title": args.title, "source": args.source}]
    if not items:
        print(json.dumps({"error": "need --spec or --file/--code"}, ensure_ascii=False))
        return 2

    results = []
    for it in items:
        results.append(process(Path(it["file"]), it["code"], it.get("title", ""), it.get("source", ""),
                               corpus, args.update_registry))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r["verdict"] in ("verified", "no_text") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
