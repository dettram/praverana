"""Раскладка корпуса: нормы → 01-Нормы, сортаменты → 02-Сортаменты, серии → 03-Серии.

Пишет карту переносов `00-Каталог/moves.csv` (from;to), чтобы всё можно было откатить.

  uv run scripts/reorganize.py            # dry-run, только отчёт
  uv run scripts/reorganize.py --apply    # выполнить
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT  # noqa: E402
from catalog_all import detect_code  # noqa: E402

KEEP_PREFIXES = ("00-Каталог", "17-Аудит-проектов", "14-BIM-шаблоны-и-модели", "_inbox-", "_архив")
TARGETS = {
    "СН": "01-Нормы/СН",
    "СП": "01-Нормы/СП",
    "СТБ": "01-Нормы/СТБ",
    "ГОСТ": "01-Нормы/ГОСТ",
    "ТКП": "01-Нормы/ТКП",
    "СНБ": "01-Нормы/СНБ",
}


def target_for(rel: str, name: str) -> tuple[str, str]:
    code, vid = detect_code(name)
    if rel.startswith("11-Серии-Металл-ЖБ/"):
        sub = Path(rel).parts[1] if len(Path(rel).parts) > 2 else ""
        return (f"03-Серии/{sub}".rstrip("/"), code or "Серия")
    if rel.startswith("15-Сортаменты-и-стандарты/"):
        return "02-Сортаменты", code
    if vid in TARGETS and Path(name).suffix.lower() in (".pdf", ".docx"):
        return TARGETS[vid], code
    if vid == "Серия":
        return "03-Серии", code
    return "", code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    moves = []
    skipped = 0
    for p in sorted(corpus.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".pdf", ".docx"):
            continue
        rel = p.relative_to(corpus).as_posix()
        if rel.startswith(KEEP_PREFIXES):
            skipped += 1
            continue
        target_dir, _ = target_for(rel, p.name)
        if not target_dir:
            skipped += 1
            continue
        dest = corpus / target_dir / p.name
        if dest.exists() and dest.stat().st_size == p.stat().st_size:
            skipped += 1
            continue
        if dest.exists():
            dest = dest.with_name(f"{dest.stem} (2){dest.suffix}")
        moves.append({"from": rel, "to": dest.relative_to(corpus).as_posix(), "size_kb": round(p.stat().st_size / 1024)})

    out = corpus / "00-Каталог" / "moves.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["from", "to", "size_kb"], delimiter=";")
        w.writeheader()
        w.writerows(moves)

    by_target = Counter(Path(m["to"]).parent.as_posix() for m in moves)
    print(f"moves={len(moves)} skipped={skipped}")
    for k, v in sorted(by_target.items()):
        print(f"  {k}: {v}")

    if not args.apply:
        print("dry-run: добавь --apply, чтобы выполнить")
        return 0

    errors = 0
    for m in moves:
        src, dst = corpus / m["from"], corpus / m["to"]
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"ERROR {m['from']}: {exc}")
    print(f"applied={len(moves) - errors} errors={errors}; map: {out}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
