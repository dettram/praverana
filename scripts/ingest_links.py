"""Скачивание и приём PDF по списку ссылок (code;url).

  uv run --with pypdf scripts/ingest_links.py --csv pdf.csv --apply
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, norm_code  # noqa: E402
from ingest_pdf import process  # noqa: E402


def download(url: str, dest: Path) -> tuple[bool, str]:
    cmd = ["curl.exe", "-sSL", "--ssl-no-revoke", "--max-time", "180",
           "-A", "Mozilla/5.0", "-o", str(dest), url]
    try:
        subprocess.run(cmd, check=False, capture_output=True, timeout=200)
    except Exception as exc:  # noqa: BLE001
        return False, f"curl: {exc}"
    if not dest.exists() or dest.stat().st_size < 50_000:
        return False, "small or missing"
    if dest.read_bytes()[:5] != b"%PDF-":
        return False, "not pdf"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    titles: dict[str, str] = {}
    reg_path = corpus / "02-Реестр.csv"
    if reg_path.exists():
        with reg_path.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                titles[norm_code(r.get("Шифр", ""))] = (r.get("Наименование") or "").strip()
    tmp = Path(tempfile.mkdtemp(prefix="ingest-"))
    results = []
    for raw in csv.DictReader(Path(args.csv).open(encoding="utf-8-sig", newline=""), delimiter=";"):
        row = {(k or "").lstrip("\ufeff").strip(): v for k, v in raw.items()}
        code = (row.get("code") or "").strip()
        url = (row.get("url") or "").strip()
        if not code or not url or "НЕ НАЙДЕНО" in url.upper():
            results.append({"code": code, "status": "no_url"})
            continue
        dest = tmp / f"{len(results)}.pdf"
        ok, why = download(url, dest)
        if not ok:
            results.append({"code": code, "status": f"download_failed: {why}"})
            continue
        if not args.apply:
            results.append({"code": code, "status": "downloaded (dry-run)"})
            continue
        r = process(dest, code, titles.get(code, ""), url, corpus, True)
        results.append({"code": code, "status": r["verdict"], "pages": r["pages"]})

    for r in results:
        print(r)
    ok = sum(1 for r in results if r.get("status") in ("verified", "no_text", "weak_text"))
    print(f"ok={ok} total={len(results)} apply={args.apply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
