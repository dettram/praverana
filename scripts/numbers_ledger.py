r"""Реестр чисел документа: все числа с единицами и файл:строка, проверка арифметики,
поиск противоречий «одна величина — разные значения» и смешения единиц.

  uv run --with pypdf --with python-docx scripts/numbers_ledger.py --path ".\объект" --out ".stroy-audit\P000"
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import pages_of  # noqa: E402

SUFFIXES = {".md", ".txt", ".csv", ".docx", ".pdf", ".xlsx"}

NUM = r"-?\d+(?:[.,]\d+)?"
UNIT = (
    r"кгс/м2|кгс/см2|кН·м|кН/м|кН·м/м|кг/м3|т/м3|м3/ч|л/с|м2|м²|м3|м³|"
    r"кПа|МПа|ГПа|кН|кг|т|мм|см|м|°C|%|шт|дБ|Вт|кВт"
)
NUM_UNIT = re.compile(rf"({NUM})\s*({UNIT})", re.IGNORECASE)
EXPR = re.compile(rf"({NUM}(?:\s*[+\-*/×·x]\s*{NUM})+)\s*=\s*({NUM})")
SAFE = re.compile(r"^[0-9.+\-*/() ]+$")
STOP_KEYS = {"более", "менее", "лее", "также", "должны", "следует"}

DIMENSION = {
    "кпа": "pressure", "мпа": "pressure", "гпа": "pressure", "кгс/м2": "pressure", "кгс/см2": "pressure",
    "кн": "force", "кгс": "force", "т": "mass", "кг": "mass",
    "кн·м": "moment", "кн/м": "line_load", "кг/м3": "density", "т/м3": "density",
    "м": "length", "мм": "length", "см": "length", "м2": "area", "м²": "area",
    "м3": "volume", "м³": "volume", "л/с": "flow", "м3/ч": "flow",
}


def to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def calc(expr: str) -> float | None:
    s = expr.replace("×", "*").replace("·", "*").replace("x", "*").replace("X", "*")
    s = s.replace(",", ".")
    if not SAFE.match(s):
        return None
    try:
        return float(eval(s, {"__builtins__": {}}, {}))  # noqa: S307 — только цифры и + - * /
    except Exception:  # noqa: BLE001
        return None


def context_key(line: str, start: int) -> str:
    head = line[:start]
    words = re.findall(r"[А-Яа-яЁёA-Za-z]{3,}", head)[-6:]
    return " ".join(w.lower() for w in words)


def scan_file(path: Path, rows: list[dict], issues: list[dict]) -> None:
    try:
        pages = pages_of(path)
    except Exception as exc:  # noqa: BLE001
        issues.append({"kind": "read", "file": str(path), "where": "",
                       "text": f"не прочитан: {type(exc).__name__}: {exc}"})
        return

    for pno, page in enumerate(pages, 1):
        for lineno, line in enumerate(page.splitlines(), 1):
            where = f"{path.name}:{pno}:{lineno}" if len(pages) > 1 else f"{path.name}:{lineno}"

            for m in NUM_UNIT.finditer(line):
                rows.append({
                    "file": path.name,
                    "where": where,
                    "value": to_float(m.group(1)),
                    "unit": m.group(2).lower(),
                    "key": context_key(line, m.start()),
                    "line": line.strip()[:300],
                    "context": line.strip()[:200],
                })

            for m in EXPR.finditer(line):
                left, right = m.group(1), to_float(m.group(2))
                got = calc(left)
                if got is None:
                    continue
                diff = abs(got - right)
                tol = max(0.05, abs(got) * 0.005)
                if diff > tol:
                    issues.append({
                        "kind": "arithmetic",
                        "file": path.name,
                        "where": where,
                        "text": f"{left} = {m.group(2)}; пересчёт даёт {got:.3f} (Δ {diff:.3f})",
                    })


def is_range_line(line: str) -> bool:
    return bool(re.search(r"\bот\s+\d|\d\s*[-–—…]\s*\d", line))


def find_contradictions(rows: list[dict]) -> list[dict]:
    issues: list[dict] = []
    grouped: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if r["key"] and len(r["key"]) >= 5 and r["key"] not in STOP_KEYS:
            grouped.setdefault((r["key"], r["unit"]), []).append(r)

    for (key, unit), items in grouped.items():
        if any(is_range_line(i.get("line", "")) for i in items):
            continue
        by_place: dict[str, set[float]] = {}
        for i in items:
            by_place.setdefault(i["where"], set()).add(round(i["value"], 6))
        if len(by_place) < 2:
            continue  # несколько чисел в одной строке — перечисление, не противоречие
        flat = sorted({v for vals in by_place.values() for v in vals})
        base = flat[0]
        if any(abs(v - base) > max(0.05, abs(base) * 0.005) for v in flat):
            places = ", ".join(sorted(by_place)[:4])
            issues.append({
                "kind": "contradiction",
                "file": items[0]["file"],
                "where": places,
                "text": f"«{key}»: значения {flat} {unit}",
            })

    by_key: dict[str, set[str]] = {}
    for r in rows:
        if r["key"] and len(r["key"]) >= 5 and r["key"] not in STOP_KEYS and r["unit"] in DIMENSION:
            by_key.setdefault(r["key"], set()).add(DIMENSION[r["unit"]])
    for key, dims in by_key.items():
        if len(dims) > 1:
            issues.append({
                "kind": "units",
                "file": "",
                "where": key,
                "text": f"смешение размерностей: {', '.join(sorted(dims))}",
            })
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--out", default="", help="каталог для ledger.csv / ledger.md / issues.md")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.path)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    files = [p for p in files if p.suffix.lower() in SUFFIXES]

    rows: list[dict] = []
    issues: list[dict] = []
    for f in files:
        scan_file(f, rows, issues)
    issues += find_contradictions(rows)

    summary = {
        "files": len(files),
        "numbers": len(rows),
        "issues": len(issues),
        "by_kind": dict(Counter(i["kind"] for i in issues)),
        "by_unit": dict(Counter(r["unit"] for r in rows).most_common(12)),
    }

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        with (out / "ledger.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["file", "where", "value", "unit", "key", "line", "context"])
            w.writeheader()
            w.writerows(rows)

        md = ["# Реестр чисел", "",
              f"Файлов: {summary['files']}; чисел с единицами: {summary['numbers']}; замечаний: {summary['issues']}.", "",
              "| Значение | Ед. | Где | Контекст |", "|---|---|---|---|"]
        for r in rows[:80]:
            md.append(f"| {r['value']:g} | {r['unit']} | {r['where']} | {r['context'][:90]} |")
        (out / "ledger.md").write_text("\n".join(md) + "\n", encoding="utf-8")

        iss = ["# Замечания реестра чисел", ""]
        for kind, title in (("arithmetic", "Арифметика"), ("contradiction", "Противоречия (кандидаты)"),
                            ("units", "Единицы (кандидаты)"), ("read", "Не прочитано")):
            group = [i for i in issues if i["kind"] == kind]
            iss += [f"## {title} ({len(group)})", ""]
            for i in group:
                iss.append(f"- `{i['where'] or i['file']}` — {i['text']}")
            iss.append("")
        (out / "issues.md").write_text("\n".join(iss) + "\n", encoding="utf-8")
        print(json.dumps({**summary, "out": str(out)}, ensure_ascii=False, indent=2))
    elif args.json:
        print(json.dumps({"summary": summary, "issues": issues[:50]}, ensure_ascii=False, indent=2))
    else:
        for i in issues[:40]:
            print(f"[{i['kind']}] {i['where']}: {i['text']}")
        print(json.dumps(summary, ensure_ascii=False))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
