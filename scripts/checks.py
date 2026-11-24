"""Точечные детерминированные проверки (без LLM-арифметики).

  uv run scripts/checks.py concrete --exposure XC3 --class C25/30
  uv run scripts/checks.py rebar --d 12 --n 4
  uv run scripts/checks.py rebar --d 10 --spacing 200
"""
from __future__ import annotations

import argparse
import json
import math
import re

# СП 5.03.01-2020, табл. Г.1 (класс экспозиции → минимальный класс бетона).
# Значения продублированы из аудиторского чек-листа (04-Аудиты/00-Обзор/Чек-лист-аудита.md).
MIN_BY_EXPOSURE = {
    "XC1": ("C20/25", "табл. Г.1"),
    "XC2": ("C25/30", "табл. Г.1"),
    "XC3": ("C30/37", "табл. Г.1"),
    "XC4": ("C30/37", "табл. Г.1"),
    "XF1": ("C30/37", "табл. Г.2"),
    "XF2": ("C25/30", "табл. Г.2"),
    "XF3": ("C30/37", "табл. Г.2"),
    "XA1": ("C30/37", "табл. Г.2"),
    "XA2": ("C35/45", "табл. Г.2"),
    "XA3": ("C35/45", "табл. Г.2"),
}

GRADES = ["C8/10", "C12/15", "C16/20", "C20/25", "C25/30", "C30/37",
          "C35/45", "C40/50", "C45/55", "C50/60", "C55/67", "C60/75"]


def grade_value(raw: str) -> tuple[str, int]:
    s = raw.upper().replace("С", "C").replace(" ", "")
    m = re.match(r"C(\d+)(?:/(\d+))?", s)
    if not m:
        raise SystemExit(f"не разобрал класс бетона: {raw!r} (ожидается C25/30)")
    return f"C{m.group(1)}/{m.group(2) or int(m.group(1)) + 5}", int(m.group(1))


def cmd_concrete(args) -> dict:
    exposure = args.exposure.upper()
    actual, actual_val = grade_value(args.cls)
    if exposure not in MIN_BY_EXPOSURE:
        return {"verdict": "не проверено",
                "reason": f"класс экспозиции {exposure} не закодирован; смотреть табл. Г.1/Г.2 СП 5.03.01-2020",
                "actual": actual}
    required, table = MIN_BY_EXPOSURE[exposure]
    req_val = grade_value(required)[1]
    ok = actual_val >= req_val
    return {
        "verdict": "соответствует" if ok else "НЕ соответствует",
        "exposure": exposure,
        "actual": actual,
        "required_min": required,
        "source": f"СП 5.03.01-2020, {table}",
        "note": "значение сверить с PDF: таблица в корпусе может терять вёрстку",
    }


def cmd_rebar(args) -> dict:
    area_one = math.pi * args.d / 4 * args.d  # πd²/4
    if args.n:
        total = area_one * args.n
        per_m = None
    elif args.spacing:
        per_m = area_one * (1000 / args.spacing)
        total = None
    else:
        return {"error": "укажи --n или --spacing"}
    mass_per_m = 0.006165 * args.d ** 2
    return {
        "d_mm": args.d,
        "area_one_mm2": round(area_one, 1),
        "n": args.n,
        "total_mm2": round(total, 1) if total else None,
        "spacing_mm": args.spacing,
        "area_per_m_mm2": round(per_m, 1) if per_m else None,
        "mass_kg_per_m": round(mass_per_m, 3),
        "note": "масса — по плотности 7850 кг/м³, справочно; сортамент — ГОСТ 34028/5781",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("concrete")
    c.add_argument("--exposure", required=True)
    c.add_argument("--class", dest="cls", required=True)

    r = sub.add_parser("rebar")
    r.add_argument("--d", type=float, required=True)
    r.add_argument("--n", type=int, default=0)
    r.add_argument("--spacing", type=float, default=0)

    args = ap.parse_args()
    result = cmd_concrete(args) if args.cmd == "concrete" else cmd_rebar(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("verdict") != "НЕ соответствует" else 1


if __name__ == "__main__":
    raise SystemExit(main())
