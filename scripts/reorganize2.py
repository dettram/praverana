"""Раскладка по регламенту: верхний уровень, имена файлов, дубли, подписи.

  uv run scripts/reorganize2.py            # dry-run
  uv run scripts/reorganize2.py --apply
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, norm_code  # noqa: E402
from catalog_all import detect_code  # noqa: E402

TOP = [
    ("17-Аудит-проектов", "04-Аудиты"),
    ("14-BIM-шаблоны-и-модели", "05-BIM"),
    ("16-Приказы-и-постановления", "07-Акты/Приказы-и-постановления"),
    ("18-Инструменты", "09-Инструменты"),
    ("19-Обучение", "08-Обучение"),
    ("12-Оформление-чертежей", "06-Справочники/Оформление-чертежей"),
    ("13-Карточки-изделий", "06-Справочники/Карточки-изделий"),
]
ROOT_FILES = {
    "01-Справочник": "06-Справочники",
    "04-Источники": "06-Справочники",
    "08-Чек-лист": "06-Справочники",
    "09-Индекс-полных-текстов": "06-Справочники",
    "10-Металл-ЖБ": "06-Справочники",
    "11-Индекс-серий": "06-Справочники/Серии",
    "11-Карточки-серий": "06-Справочники/Серии",
    "11-Реестр-серий": "06-Справочники/Серии",
    "11-Серии-Металл-ЖБ": "06-Справочники/Серии",
    "ПЛАН-РАЗВИТИЯ": "06-Справочники",
    "07-Учебный-конспект": "08-Обучение",
}
SERIES_RE = re.compile(r"Серия\s*([0-9][0-9.\-/]*)\s*[-—]?\s*(.*)", re.IGNORECASE)


def clean_title(s: str) -> str:
    s = re.sub(r"\(\d+\s*с\.\)", "", s)
    s = re.sub(r"^(txt|or|pz|so|i1)[-_]", "", s, flags=re.I)
    s = re.sub(r"^\d{2}-", "", s)
    s = re.sub(r"\s+", " ", s).strip(" -—,.")
    return s


def load_titles(corpus: Path) -> dict[str, str]:
    reg = corpus / "02-Реестр.csv"
    out: dict[str, str] = {}
    if not reg.exists():
        return out
    for r in csv.DictReader(reg.open(encoding="utf-8-sig", newline=""), delimiter=";"):
        code = norm_code(r.get("Шифр", ""))
        name = (r.get("Наименование") or "").strip()
        if code and name:
            out.setdefault(code, name)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    corpus = Path(args.corpus)
    titles = load_titles(corpus)
    moves: list[tuple[Path, Path, str]] = []

    # 1. верхний уровень
    for src_name, dst_name in TOP:
        src = corpus / src_name
        if src.exists():
            moves.append((src, corpus / dst_name, "top"))

    for p in sorted(corpus.iterdir()):
        if p.is_file() and p.stem in ROOT_FILES and p.suffix.lower() in (".md", ".docx", ".pdf", ".xlsx", ".csv"):
            moves.append((p, corpus / ROOT_FILES[p.stem] / p.name, "root"))

    # 2. 03-Тексты-PDF: СП в нормы, остальное в акты
    src = corpus / "03-Тексты-PDF"
    if src.exists():
        for f in sorted(src.rglob("*")):
            if f.is_file():
                if "СП 1.02.01" in f.name:
                    moves.append((f, corpus / "01-Нормы/СП" / f.name, "law"))
                else:
                    moves.append((f, corpus / "07-Акты/Законы-и-ТР" / f.name, "law"))
        moves.append((src, corpus / "_архив/03-Тексты-PDF", "empty"))

    # 3. остатки 05 -> пакеты/тексты
    src = corpus / "05-Полные-тексты-PDF"
    if src.exists():
        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            dst = "01-Нормы/Пакеты" if f.suffix.lower() == ".pdf" else "01-Нормы/_тексты"
            moves.append((f, corpus / dst / f.name, "package"))
        moves.append((src, corpus / "_архив/05-Полные-тексты-PDF", "empty"))

    # 4. переименование внутри 01/02
    renames = []
    for base in ("01-Нормы", "02-Сортаменты"):
        root = corpus / base
        if not root.exists():
            continue
        for f in sorted(root.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in (".pdf", ".docx"):
                continue
            code, vid = detect_code(f.name)
            if not code:
                continue
            title = titles.get(code, "")
            if not title:
                rest = f.name
                m = re.search(re.escape(code.split()[0]) + r"[^ ]*\s*[-—]?\s*(.*)", f.name, re.I)
                title = clean_title(rest)
            title = clean_title(title)[:150]
            if not title:
                continue
            safe_code = re.sub(r'[\\/:*?"<>|]', "-", code)
            safe_title = re.sub(r'[\\/:*?"<>|]', "-", title)
            new = f.with_name(f"{safe_code} — {safe_title}{f.suffix.lower()}")
            if new != f:
                renames.append((f, new, "rename"))

    # 5. дубли по (code, ext) — оставить самый крупный
    dups = []
    for base in ("01-Нормы", "02-Сортаменты"):
        root = corpus / base
        if not root.exists():
            continue
        groups: dict[tuple[str, str], list[Path]] = defaultdict(list)
        for f in root.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".pdf", ".docx"):
                code, _ = detect_code(f.name)
                if code:
                    groups[(code, f.suffix.lower())].append(f)
        for (code, ext), files in groups.items():
            if len(files) < 2:
                continue
            files.sort(key=lambda p: p.stat().st_size, reverse=True)
            for extra in files[1:]:
                dups.append((extra, corpus / "_архив/дубли" / extra.name, "dup"))

    all_moves = moves + renames
    out = corpus / "00-Каталог" / "moves2.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["from", "to", "kind"])
        for s, d, k in all_moves:
            w.writerow([s.relative_to(corpus).as_posix(), d.relative_to(corpus).as_posix(), k])

    print("kinds:", dict(Counter(k for _, _, k in all_moves)), "total:", len(all_moves))
    for s, d, k in all_moves[:12]:
        print(f"  [{k}] {s.relative_to(corpus).as_posix()} -> {d.relative_to(corpus).as_posix()}")

    if not args.apply:
        print("dry-run: добавь --apply")
        return 0

    errors = 0
    for s, d, k in all_moves:
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            if s.is_dir():
                if d.exists():
                    for child in s.rglob("*"):
                        if child.is_file():
                            target = d / child.relative_to(s)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(child), str(target))
                    shutil.rmtree(s, ignore_errors=True)
                else:
                    shutil.move(str(s), str(d))
            else:
                if d.exists() and d.stat().st_size == s.stat().st_size:
                    s.unlink()
                else:
                    shutil.move(str(s), str(d))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"ERROR {s}: {exc}")

    # дубли считаем после переименований
    dup_moves: list[tuple[Path, Path, str]] = []
    for base in ("01-Нормы", "02-Сортаменты"):
        root = corpus / base
        if not root.exists():
            continue
        groups: dict[tuple[str, str], list[Path]] = defaultdict(list)
        for f in root.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".pdf", ".docx"):
                code, _ = detect_code(f.name)
                if code:
                    groups[(code, f.suffix.lower())].append(f)
        for (code, ext), files in groups.items():
            if len(files) < 2:
                continue
            files.sort(key=lambda p: p.stat().st_size, reverse=True)
            for extra in files[1:]:
                dup_moves.append((extra, corpus / "_архив/дубли" / extra.name, "dup"))

    if dup_moves:
        with out.open("a", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            for s, d, k in dup_moves:
                w.writerow([s.relative_to(corpus).as_posix(), d.relative_to(corpus).as_posix(), k])
        for s, d, k in dup_moves:
            try:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(s), str(d))
            except Exception as exc:  # noqa: BLE001
                errors += 1
                print(f"ERROR dup {s}: {exc}")

    print(f"applied={len(all_moves) + len(dup_moves) - errors} dups={len(dup_moves)} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
