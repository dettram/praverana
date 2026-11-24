"""Оценка базы 0–10 по измеримым критериям.

  uv run scripts/score.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, norm_code  # noqa: E402


def main() -> int:
    corpus = Path(CORPUS_DEFAULT)
    reg_path = corpus / "02-Реестр.csv"
    rows = list(csv.DictReader(reg_path.open(encoding="utf-8-sig", newline=""), delimiter=";"))
    rows = [{k: v for k, v in r.items() if k is not None} for r in rows]

    active = [r for r in rows if (r.get("Статус на 18.11.2026") or "").startswith("действ")]
    unverified = [r for r in rows if "не проверен" in (r.get("Статус на 18.11.2026") or "")]
    inactive = [r for r in rows if any(k in (r.get("Статус на 18.11.2026") or "").lower()
                                        for k in ("не действ", "отмен", "замен", "не применя"))]

    have = set()
    files = 0
    scans = 0
    for man in corpus.glob("_inbox-*/manifest.csv"):
        for m in csv.DictReader(man.open(encoding="utf-8-sig", newline=""), delimiter=";"):
            have.add(norm_code(m["code"]))
            files += 1
            if (m.get("verdict") or "") in ("no_text", "weak_text"):
                scans += 1
    cat_all = corpus / "00-Каталог" / "catalog-all.csv"
    if cat_all.exists():
        for r in csv.DictReader(cat_all.open(encoding="utf-8-sig", newline=""), delimiter=";"):
            if r.get("ext") in (".pdf", ".docx") and (r.get("code") or "").strip():
                have.add(norm_code(r["code"]))

    active_codes = {norm_code(r["Шифр"]) for r in active}
    covered = len(active_codes & have)

    cit_ok = cit_total = 0
    ca = corpus / "_inbox-2026-11-23" / "cite-audit.md"
    if ca.exists():
        text = ca.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"цитат: (\d+); подтверждено: (\d+)", text)
        if m:
            cit_total, cit_ok = int(m.group(1)), int(m.group(2))

    dup_groups = 0
    dm = corpus / "00-Каталог" / "duplicates.md"
    if dm.exists():
        m = re.search(r"Шифров с несколькими файлами: \*\*(\d+)\*\*", dm.read_text(encoding="utf-8", errors="replace"))
        if m:
            dup_groups = int(m.group(1))

    completeness = min(10.0, 10.0 * covered / max(1, len(active_codes)))
    currency = 10.0 * (1 - len(unverified) / max(1, len(rows)))
    quality = 10.0 * (1 - scans / max(1, files))
    structure = 9.0 if dm.exists() else 5.0
    verifiability = 10.0 * (cit_ok / max(1, cit_total)) if cit_total else 0.0
    cleanliness = 9.0 if dup_groups <= 30 else 7.0

    total = (0.30 * completeness + 0.20 * currency + 0.15 * quality +
             0.10 * structure + 0.20 * verifiability + 0.05 * cleanliness)

    audit = (0.40 * verifiability + 0.20 * structure + 0.20 * quality +
             0.10 * cleanliness + 0.10 * currency)
    overall = 0.5 * total + 0.5 * audit

    print(f"active={len(active)} covered={covered} unverified={len(unverified)} inactive={len(inactive)}")
    print(f"files={files} scans={scans} citations={cit_ok}/{cit_total} dup_groups={dup_groups}")
    print(f"completeness={completeness:.1f} currency={currency:.1f} quality={quality:.1f} "
          f"structure={structure:.1f} verifiability={verifiability:.1f} cleanliness={cleanliness:.1f}")
    print(f"FUND={total:.1f}/10  AUDIT={audit:.1f}/10  OVERALL={overall:.1f}/10")

    report = [
        "# Оценка базы",
        "",
        f"Активных норм: {len(active)}; с файлом: {covered}; не проверено: {len(unverified)}; отменено: {len(inactive)}.",
        f"Файлов принято: {files}; сканов: {scans}; цитаты: {cit_ok}/{cit_total}; групп дублей: {dup_groups}.",
        "",
        "| Критерий | Балл |",
        "|---|---|",
        f"| Полнота фонда | {completeness:.1f} |",
        f"| Актуальность статусов | {currency:.1f} |",
        f"| Качество текстов | {quality:.1f} |",
        f"| Систематизация | {structure:.1f} |",
        f"| Проверяемость | {verifiability:.1f} |",
        f"| Чистота | {cleanliness:.1f} |",
        "",
        f"**Фонд: {total:.1f}/10 · Рабочая база: {audit:.1f}/10 · Итог: {overall:.1f}/10**",
        "",
        "Пересчёт: `uv run scripts/score.py`.",
    ]
    (corpus / "00-Каталог" / "score.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
