"""Слияние результатов верификации в 02-Реестр.csv.

  uv run scripts/merge_verification.py --csv verified.csv
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, norm_code, status_key  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--min-confidence", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rank = {"low": 0, "medium": 1, "high": 2}
    corpus = Path(args.corpus)
    reg = corpus / "02-Реестр.csv"
    rows = list(csv.DictReader(reg.open(encoding="utf-8-sig", newline=""), delimiter=";"))
    rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
    by_code = {norm_code(r["Шифр"]): r for r in rows if (r.get("Шифр") or "").strip()}

    updated = skipped = 0
    for raw in csv.DictReader(Path(args.csv).open(encoding="utf-8-sig", newline=""), delimiter=";"):
        v = {(k or "").lstrip("\ufeff").strip(): val for k, val in raw.items()}
        code = norm_code(v.get("code", ""))
        conf = (v.get("confidence") or "low").strip().lower()
        if code not in by_code or rank.get(conf, 0) < rank[args.min_confidence]:
            skipped += 1
            continue
        if (v.get("status") or "").strip().lower() in ("не найдено", ""):
            skipped += 1
            continue
        r = by_code[code]
        if not (r.get("Наименование") or "").strip() and v.get("name"):
            r["Наименование"] = v["name"].strip()
        r[status_key(r) or f"Статус на {date.today():%d.%m.%Y}"] = v["status"].strip()
        if v.get("replacement"):
            r["Заменяет / чем заменён"] = v["replacement"].strip()
        src = (r.get("Источник") or "").strip()
        add = v.get("source", "").strip()
        if add and add not in src:
            r["Источник"] = f"{src}; {add}" if src else add
        updated += 1

    print(f"updated={updated} skipped={skipped}")
    if args.write and updated:
        backup = reg.with_name(f"02-Реестр.backup-{date.today():%Y%m%d}-verif.csv")
        if not backup.exists():
            shutil.copy2(reg, backup)
        with reg.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";", lineterminator="\r\n")
            w.writeheader()
            w.writerows(rows)
        print("written", reg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
