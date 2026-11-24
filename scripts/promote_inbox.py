"""Перенос принятых PDF из _inbox в 01-Нормы/02-Сортаменты и правка manifest.csv.

  uv run scripts/promote_inbox.py --apply
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, norm_code  # noqa: E402


def target_for(code: str, assort: set[str]) -> str:
    up = code.upper()
    if up.startswith("EN "):
        return "01-Нормы/EN"
    if up.startswith("СЕРИЯ"):
        return "03-Серии"
    if up.startswith("ГОСТ") and code in assort:
        return "02-Сортаменты"
    vid = code.split()[0] if code.split() else ""
    if vid in ("СН", "СП", "СТБ", "ГОСТ", "ТКП", "СНБ"):
        return f"01-Нормы/{vid}"
    return "01-Нормы/Прочее"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    corpus = Path(args.corpus)

    assort: set[str] = set()
    reg = corpus / "02-Сортаменты" / "_индекс" / "15-Реестр.csv"
    if reg.exists():
        for r in csv.DictReader(reg.open(encoding="utf-8-sig", newline=""), delimiter=";"):
            assort.add(norm_code(r.get("Документ", "")))

    moved = skipped = 0
    for man in sorted(corpus.glob("_inbox-*/manifest.csv")):
        rows = list(csv.DictReader(man.open(encoding="utf-8-sig", newline=""), delimiter=";"))
        rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
        changed = False
        for r in rows:
            code = norm_code(r.get("code", ""))
            rel = (r.get("file") or "").replace("\\", "/")
            if not code or not rel:
                continue
            src = corpus / rel
            if not src.exists():
                continue
            tgt_dir = corpus / target_for(code, assort)
            tgt = tgt_dir / src.name
            if tgt.exists():
                if tgt.stat().st_size == src.stat().st_size:
                    if args.apply:
                        src.unlink()
                    skipped += 1
                    r["file"] = tgt.relative_to(corpus).as_posix()
                    changed = True
                    continue
                tgt = tgt.with_name(f"{tgt.stem} (2){tgt.suffix}")
            if args.apply:
                tgt_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(tgt))
            r["file"] = tgt.relative_to(corpus).as_posix()
            changed = True
            moved += 1
        if args.apply and changed:
            with man.open("w", encoding="utf-8-sig", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";")
                w.writeheader()
                w.writerows(rows)

    print(f"moved={moved} skipped_same={skipped} apply={args.apply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
