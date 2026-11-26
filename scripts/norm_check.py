r"""Проверка нормативных ссылок проекта по реестру РБ (состояние 18.11.2026).

  uv run scripts/norm_check.py --path ".\объект" --out ".stroy-audit\P000\norms.md"
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CODE_RE,
    CORPUS_DEFAULT,
    CURATED_OUTDATED,
    extract_citations,
    norm_code,
    pages_of,
    status_of,
    year_of,
)

TEXT_SUFFIXES = {".md", ".txt", ".csv", ".docx", ".pdf", ".xlsx"}


def load_registry(corpus: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    extra = Path(__file__).resolve().parent.parent / "data" / "registry-extra.csv"
    paths = [corpus / "02-Реестр.csv", extra]
    rows: dict[str, dict] = {}
    replaced_by: dict[str, dict] = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh, delimiter=";"):
                raw = (row.get("Шифр") or "").strip()
                if not CODE_RE.search(raw):
                    continue
                code = norm_code(raw)
                rows.setdefault(code, row)
                status = status_of(row).lower()
                if "не действ" in status or "отмен" in status:
                    # у недействующей строки поле содержит её замену: регистрируем замену как действующую
                    for m in CODE_RE.finditer(row.get("Заменяет / чем заменён") or ""):
                        new = norm_code(m.group(0))
                        if new == code:
                            continue
                        rows.setdefault(new, {
                            "Шифр": new,
                            "Статус": "действует (по замене)",
                            "Заменяет / чем заменён": f"заменяет {code}",
                            "Источник": row.get("Источник", ""),
                        })
                    continue
                old_field = row.get("Заменяет / чем заменён") or ""
                for m in CODE_RE.finditer(old_field):
                    old = norm_code(m.group(0))
                    if old != code:
                        replaced_by.setdefault(old, row)
    return rows, replaced_by


def registry_date(corpus: Path) -> str:
    """Дата из заголовка «Статус на <дата>»; не привязана к конкретному дню."""
    extra = Path(__file__).resolve().parent.parent / "data" / "registry-extra.csv"
    for path in (corpus / "02-Реестр.csv", extra):
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as fh:
            header = next(csv.reader(fh, delimiter=";"), [])
        for name in header:
            m = re.match(r"^статус\s+на\s+(.+)$", name.strip(), re.I) if name else None
            if m:
                return m.group(1).strip() or "дата не определена"
    return "дата не определена"


def _close(code: str, registry: dict[str, dict], active_only: bool = False, cutoff: float = 0.82) -> str | None:
    import difflib

    pool = [c for c, r in registry.items()
            if not active_only or status_of(r).startswith("действ")]
    matches = difflib.get_close_matches(code, pool, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def classify(code: str, registry: dict[str, dict], replaced_by: dict[str, dict]) -> tuple[str, str]:
    """→ (severity, message): error | warn | ok."""
    if code.upper().startswith("СНИП"):
        return "error", "СНиП в РБ не применяются с 21.01.2025 (пост. МАиС № 7); ссылаться на СН/СП"
    if code in CURATED_OUTDATED:
        new, why = CURATED_OUTDATED[code]
        return "error", f"{why}; замена — {new}"
    if year_of(code) is None and not code.startswith("ГОСТ"):
        hint = _close(code, registry)
        return "warn", "шифр без года — статус не определить" + (f"; возможно, {hint}" if hint else "")

    row = registry.get(code)
    if row:
        status = status_of(row).lower()
        if status.startswith("действ"):
            return "ok", status_of(row) or "действует"
        if "не проверен" in status:
            hint = _close(code, registry, active_only=True)
            tail = f"; возможно, имелось в виду {hint}" if hint else ""
            return "warn", "статус не подтверждён (строка собрана автоматически)" + tail
        if "не вступ" in status:
            return "warn", f"принят, но не вступил: {status_of(row)}"
        if "не применя" in status:
            return "error", f"не применяется в РБ (п. 1.5 Указа № 217); {row.get('Заменяет / чем заменён')}"
        if "замен" in status or "не действ" in status or "отмен" in status:
            return "error", f"статус: {status_of(row)}; {row.get('Заменяет / чем заменён')}"
        if not status:
            return "warn", "статус не подтверждён: в реестре нет колонки или значения статуса"
        return "warn", f"статус не распознан: {status_of(row)}"

    new_row = replaced_by.get(code)
    if new_row:
        return "error", f"заменён на {norm_code(new_row['Шифр'])} (реестр)"

    import difflib

    close = difflib.get_close_matches(code, list(registry), n=1, cutoff=0.88)
    if close:
        return "warn", f"нет в реестре; возможно, имелось в виду {close[0]}"
    return "warn", "нет в реестре — проверить на pravo.by / minskgns.by"


def collect(path: Path, skip: set[Path] | None = None) -> list[dict]:
    skip = skip or set()
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    found: list[dict] = []
    for file in files:
        if file.suffix.lower() not in TEXT_SUFFIXES or file.resolve() in skip:
            continue
        try:
            pages = pages_of(file)
        except Exception as exc:  # noqa: BLE001
            found.append({"file": str(file), "code": "", "line": 0, "severity": "warn",
                          "message": f"не прочитан: {type(exc).__name__}: {exc}", "context": ""})
            continue
        for pno, page in enumerate(pages, 1):
            for cit in extract_citations(page):
                found.append({
                    "file": str(file),
                    "page": pno,
                    "code": cit["code"],
                    "line": cit["line"],
                    "context": cit["context"],
                })
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--coverage", action="store_true", help="какие нормы реестра есть в корпусе текстом")
    args = ap.parse_args()

    registry, replaced_by = load_registry(Path(args.corpus))
    if not registry:
        print(json.dumps({"error": "registry not found", "path": str(Path(args.corpus) / "02-Реестр.csv")},
                         ensure_ascii=False))
        return 2

    rows = collect(Path(args.path), {Path(args.out).resolve()} if args.out else set())
    for r in rows:
        if not r["code"]:
            continue
        sev, msg = classify(r["code"], registry, replaced_by)
        r["severity"], r["message"] = sev, msg

    # уникальные пары (файл, шифр) с первыми строками
    grouped: dict[tuple[str, str], dict] = {}
    for r in rows:
        key = (r["file"], r["code"])
        if key not in grouped:
            grouped[key] = {**r, "lines": []}
        if r["code"]:
            loc = r.get("line") or r.get("page")
            if loc and loc not in grouped[key]["lines"] and len(grouped[key]["lines"]) < 3:
                grouped[key]["lines"].append(loc)

    items = list(grouped.values())
    errors = [i for i in items if i.get("severity") == "error"]
    warns = [i for i in items if i.get("severity") == "warn"]
    oks = [i for i in items if i.get("severity") == "ok"]

    if args.json:
        print(json.dumps({"errors": errors, "warnings": warns, "ok": len(oks),
                          "citations": len([r for r in rows if r["code"]])}, ensure_ascii=False, indent=2))
    lines = [
        "# Проверка нормативных ссылок",
        "",
        f"Источник статусов: `02-Реестр.csv` + `data/registry-extra.csv` (проверено 20.11.2026). Проверено ссылок: {len([r for r in rows if r['code']])}.",
        "",
        f"- блокеров: **{len(errors)}**",
        f"- предупреждений: **{len(warns)}**",
        f"- подтверждено действующими: **{len(oks)}**",
        "",
        "## Блокеры",
        "",
        "| Шифр в проекте | Где | Проблема |",
        "|---|---|---|",
    ]
    for it in errors:
        where = f"{Path(it['file']).name}:{','.join(map(str, it['lines']))}"
        lines.append(f"| {it['code']} | {where} | {it['message']} |")
    if not errors:
        lines.append("| — | — | не найдено |")
    lines += ["", "## Предупреждения", "", "| Шифр | Где | Комментарий |", "|---|---|---|"]
    for it in warns:
        where = f"{Path(it['file']).name}:{','.join(map(str, it['lines']))}"
        lines.append(f"| {it['code'] or '—'} | {where} | {it['message']} |")
    if not warns:
        lines.append("| — | — | не найдено |")

    if args.coverage:
        corpus_files = [p.name for p in Path(args.corpus).rglob("*") if p.is_file()]
        missing = [c for c in registry if not any(c.replace(" ", "") in f.replace(" ", "") for f in corpus_files)]
        lines += ["", "## Покрытие корпуса", "",
                  f"Шифров в реестре: {len(registry)}; без одноимённого файла: {len(missing)}.", ""]
        lines += [f"- {c}" for c in sorted(missing)[:80]]

    text = "\n".join(lines) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"written: {out}")
    else:
        print(text)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
