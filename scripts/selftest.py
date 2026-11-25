"""Самотест скилла: без сети, без корпуса, без внешних зависимостей.

  uv run scripts/selftest.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_index  # noqa: E402
import checks  # noqa: E402
import norm_check  # noqa: E402
import numbers_ledger  # noqa: E402
from common import extract_citations, norm_code, year_of  # noqa: E402

FAILED: list[str] = []


def eq(name: str, got, want) -> None:
    if got != want:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")


def close(name: str, got: float, want: float, tol: float = 0.01) -> None:
    if abs(got - want) > tol:
        FAILED.append(f"{name}: got {got}, want {want}")


def test_codes() -> None:
    eq("code-simple", norm_code("сн  2.01.04 - 2025*"), "СН 2.01.04-2025")
    eq("code-gost", norm_code("гост 30245 – 2012"), "ГОСТ 30245-2012")
    eq("code-snip", norm_code("СНиП II-23-81*"), "СНиП II-23-81")
    eq("code-en", norm_code("СТБ EN 1992-1-1"), "СТБ EN 1992-1-1")
    eq("year-2025", year_of("СН 2.01.04-2025"), 2025)
    eq("year-83", year_of("ГОСТ 26020-83"), 1983)

    text = "Нагрузки — по СН 2.01.04-2025 и СН 2.01.05-2025; СНиП II-23-81* не применять."
    cites = extract_citations(text)
    eq("citations-count", len(cites), 3)
    eq("citations-first", cites[0]["code"], "СН 2.01.04-2025")


def test_registry_logic() -> None:
    registry = {
        "СП 5.03.01-2020": {"Шифр": "СП 5.03.01-2020", "Статус": "действует",
                            "Заменяет / чем заменён": "—"},
        "СН 3.03.01-2026": {"Шифр": "СН 3.03.01-2026",
                            "Статус": "приняты, не вступили в силу",
                            "Заменяет / чем заменён": "СН 3.03.01-2019"},
    }
    replaced = {"СН 2.01.04-2019": {"Шифр": "СН 2.01.04-2025"}}

    eq("active", norm_check.classify("СП 5.03.01-2020", registry, replaced)[0], "ok")
    eq("pending", norm_check.classify("СН 3.03.01-2026", registry, replaced)[0], "warn")
    eq("replaced", norm_check.classify("СН 2.01.04-2019", registry, replaced)[0], "error")
    eq("snip", norm_check.classify("СНиП II-23-81", registry, replaced)[0], "error")
    eq("unknown", norm_check.classify("СН 9.99.99-2020", registry, replaced)[0], "warn")
    eq("no-year", norm_check.classify("СН 2.01.04", registry, replaced)[0], "warn")


def test_arithmetic() -> None:
    close("calc-mul", numbers_ledger.calc("2,5 * 4"), 10.0)
    close("calc-chain", numbers_ledger.calc("1,2 + 3 * 2"), 7.2)
    eq("calc-safe", numbers_ledger.calc("__import__('os')"), None)

    rows, issues = [], []
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "calc.md"
        f.write_text("Итого: 2,5 × 4 = 11 кН.\nНагрузка 12,5 кПа.\n", encoding="utf-8")
        numbers_ledger.scan_file(f, rows, issues)
    eq("ledger-numbers", len(rows), 2)
    eq("arith-flagged", [i["kind"] for i in issues], ["arithmetic"])


def test_checks() -> None:
    class A:
        exposure, cls = "XC3", "C25/30"

    r = checks.cmd_concrete(A())
    eq("concrete-bad", r["verdict"], "НЕ соответствует")
    A.cls = "C30/37"
    eq("concrete-ok", checks.cmd_concrete(A())["verdict"], "соответствует")

    class B:
        d, n, spacing = 12, 4, 0

    close("rebar-4d12", checks.cmd_rebar(B())["total_mm2"], 452.4, tol=0.2)


def test_index() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "corpus"
        root.mkdir()
        (root / "02-Реестр.csv").write_text("№;Шифр\n1;СН 2.01.04-2025\n", encoding="utf-8-sig")
        (root / "norm.md").write_text("# СН 2.01.04-2025\nСнеговые нагрузки.\n\n" + "текст " * 100,
                                      encoding="utf-8")
        out = Path(tmp) / "index.sqlite"
        argv = sys.argv
        try:
            sys.argv = ["build_index.py", "--corpus", str(root), "--out", str(out), "--limit", "5"]
            eq("index-rc", build_index.main(), 0)
        finally:
            sys.argv = argv
        eq("index-created", out.exists(), True)


def main() -> int:
    for fn in (test_codes, test_registry_logic, test_arithmetic, test_checks, test_index):
        fn()
    if FAILED:
        print(f"FAILED {len(FAILED)}:")
        for f in FAILED:
            print("  -", f)
        return 1
    print("OK: 5 групп проверок пройдены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
