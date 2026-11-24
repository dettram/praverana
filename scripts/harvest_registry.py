"""Сборка реестра ТНПА РБ из выгрузок официальных источников (офлайн-парсер + слияние).

Источники (файлы скачиваются отдельно, см. references/norm-status-by.md):
  --stn-json       текст страницы stn.by/standartisation/splist (JSON Exa или сырой текст)
  --minskgsn-html  таблица СН с датами введения (minskgsn.by)
  --mchs-pdf       перечень ТНПА МЧС (PDF)
  --minenergo-html список ТКП Минэнерго
  --corpus         корпус: коды, встречающиеся в проектных текстах (≥ --min-hits раз)

  uv run scripts/harvest_registry.py --stn-json ... --registry "…02-Реестр.csv" --write
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CODE_RE, CORPUS_DEFAULT, CURATED_OUTDATED, clean, extract_citations, norm_code, year_of,
)

COLUMNS = ["№", "Шифр", "Наименование", "Вид", "Введён (утверждён)",
           "Последнее изменение", "Статус на 18.11.2026", "Заменяет / чем заменён", "Источник"]

VID = {
    "СН": "СН", "СП": "СП", "ТКП": "ТКП", "ГОСТ": "ГОСТ", "СТБ": "СТБ", "СНБ": "СНБ",
}


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.cell: list[str] = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell, self.in_cell = [], True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.row.append(" ".join("".join(self.cell).split()))
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)


def vid_of(code: str) -> str:
    for prefix, label in VID.items():
        if code.upper().startswith(prefix):
            return label
    return ""


def stn_rows(path: Path) -> tuple[dict[str, dict], dict[str, set[int]]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if raw.lstrip().startswith("{"):
        data = json.loads(raw)
        raw = (data.get("results") or [{}])[0].get("text") or ""
    found: dict[str, dict] = {}
    changes: dict[str, set[int]] = {}
    for line in raw.splitlines():
        line = clean(line).strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= {"-", " "}:
            continue
        text = cells[1]
        m = CODE_RE.search(text)
        if not m:
            continue
        code = norm_code(m.group(0))
        if "ИЗМЕНЕНИЕ" in text.upper():
            num = re.search(r"ИЗМЕНЕНИЕ\s*№?\s*(\d+)", text.upper())
            if num:
                changes.setdefault(code, set()).add(int(num.group(1)))
            continue
        name = re.sub(rf"^{re.escape(m.group(0))}\s*", "", text).strip(" «»\"—-")
        name = re.sub(r"^" + re.escape(code) + r"\s*", "", name, flags=re.I).strip(" «»\"—-")
        src = cells[2] if len(cells) > 2 else ""
        post = cells[3] if len(cells) > 3 else ""
        if code in found:
            continue
        found[code] = {
            "Шифр": code,
            "Наименование": name,
            "Вид": vid_of(code),
            "Введён (утверждён)": post if post and post != "—" else "",
            "Последнее изменение": "",
            "Статус на 18.11.2026": "действует",
            "Заменяет / чем заменён": "" if src in ("", "—") else src,
            "Источник": "stn.by/standartisation/splist",
        }
    for code, nums in changes.items():
        row = found.get(code)
        if row:
            row["Последнее изменение"] = "изм. " + ", ".join(f"№{n}" for n in sorted(nums))
    return found, changes


def minskgsn_rows(path: Path) -> dict[str, dict]:
    p = Table()
    p.feed(path.read_text(encoding="utf-8", errors="replace"))
    out: dict[str, dict] = {}
    for row in p.rows[1:]:
        if len(row) < 2:
            continue
        m = CODE_RE.search(row[0])
        if not m:
            continue
        code = norm_code(m.group(0))
        name = row[0][m.end():].strip(" «»\"—-")
        date = row[1].strip()
        out[code] = {"Наименование": name, "Введён (утверждён)": date, "Вид": vid_of(code)}
    return out


def mchs_rows(path: Path) -> dict[str, dict]:
    from pypdf import PdfReader

    text = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    lines = [clean(x).strip() for x in text.splitlines() if x.strip()]
    out: dict[str, dict] = {}
    i = 0
    while i < len(lines):
        m = re.match(r"^(ТКП|СН|СП)\s*\d+(?:[.\-]\d+)*-\d{4}", lines[i])
        if not m:
            i += 1
            continue
        code = norm_code(m.group(0))
        name_parts, post, j = [], "", i + 1
        while j < len(lines) and j < i + 12:
            if re.match(r"^(ТКП|СН|СП|ГОСТ|СТБ)\s*\d", lines[j]) and j > i + 1:
                break
            if lines[j].lower().startswith(("постановление", "приказ")):
                post = lines[j]
                break
            if lines[j] != "(02300)" and not re.match(r"^\(\d{5}\)$", lines[j]):
                name_parts.append(lines[j])
            j += 1
        out.setdefault(code, {
            "Шифр": code,
            "Наименование": " ".join(name_parts)[:300],
            "Вид": vid_of(code),
            "Введён (утверждён)": post,
            "Последнее изменение": "",
            "Статус на 18.11.2026": "действует",
            "Заменяет / чем заменён": "",
            "Источник": "mchs.gov.by, перечень на 01.11.2026",
        })
        i = j + 1
    return out


def minenergo_rows(path: Path) -> dict[str, dict]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    lines = [clean(x).replace("&nbsp;", " ").strip() for x in raw.splitlines()]
    lines = [x for x in lines if x]
    out: dict[str, dict] = {}
    for i, line in enumerate(lines):
        m = re.match(r"^ТКП\s*\d+(?:[.\-]\d+)*-\d{4}", line)
        if not m or "Изменение" in line:
            continue
        code = norm_code(m.group(0))
        name = ""
        for cand in lines[i + 1:i + 4]:
            if cand and not cand.startswith(("ТКП", "Постановление", "Приказ", "Изменение")):
                name = cand
                break
        post = ""
        for cand in lines[i + 1:i + 6]:
            if cand.lower().startswith(("постановление", "приказ")):
                post = cand
                break
        out.setdefault(code, {
            "Шифр": code,
            "Наименование": name[:300],
            "Вид": "ТКП",
            "Введён (утверждён)": post,
            "Последнее изменение": "",
            "Статус на 18.11.2026": "действует",
            "Заменяет / чем заменён": "",
            "Источник": "minenergo.gov.by/law/tnpa",
        })
    return out


def corpus_rows(corpus: Path, known: set[str], min_hits: int = 2) -> dict[str, dict]:
    counts: dict[str, int] = {}
    roots = [corpus / "04-Аудиты"]
    seen_files = 0
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.suffix.lower() not in (".md", ".txt", ".csv") or not f.is_file():
                continue
            if f.stat().st_size > 500_000:
                continue
            seen_files += 1
            text = f.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if len(line) > 5000:
                    continue
                for cit in extract_citations(line):
                    counts[cit["code"]] = counts.get(cit["code"], 0) + 1
            if seen_files % 50 == 0:
                print(f"[corpus] files={seen_files} codes={len(counts)}", file=sys.stderr, flush=True)
    out: dict[str, dict] = {}
    for code, n in counts.items():
        if code in known or n < min_hits:
            continue
        if not code.upper().startswith(("ГОСТ", "СТБ", "ТКП")):
            continue
        y = year_of(code)
        if y is None or not (1950 <= y <= 2030):
            continue
        out[code] = {
            "Шифр": code,
            "Наименование": "",
            "Вид": vid_of(code),
            "Введён (утверждён)": "",
            "Последнее изменение": "",
            "Статус на 18.11.2026": "не проверен",
            "Заменяет / чем заменён": "",
            "Источник": f"проектные тексты (встречается {n} раз)",
        }
    return out


def reconcile_statuses(rows: dict[str, dict], protected: set[str]) -> int:
    """Помечаем недействующими только автоматически добавленные строки.

    Курируемые строки исходного реестра не трогаем: там статус выставлен человеком
    (например, СН 2.02.05-2020 действует, хотя СП 2.02.05-2026 её дублирует по области).
    """
    fixed = 0
    for code in protected:
        row = rows.get(code)
        if not row:
            continue
        status = (row.get("Статус на 18.11.2026") or "").lower()
        if "не действ" in status or "не вступ" in status:
            continue
        for m in CODE_RE.finditer(row.get("Заменяет / чем заменён") or ""):
            old = norm_code(m.group(0))
            if old == code or old not in rows or old in protected:
                continue
            old_row = rows[old]
            if (old_row.get("Статус на 18.11.2026") or "").lower().startswith("действ"):
                old_row["Статус на 18.11.2026"] = "не действует"
                old_row["Заменяет / чем заменён"] = f"заменён на {code}"
                fixed += 1
    for old, (new, why) in CURATED_OUTDATED.items():
        if old in rows and old not in protected:
            before = (rows[old].get("Статус на 18.11.2026") or "").lower()
            if not before.startswith("не действ"):
                rows[old]["Статус на 18.11.2026"] = "не действует"
                rows[old]["Заменяет / чем заменён"] = f"заменён на {new} ({why})"
                fixed += 1
    return fixed


def load_existing(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter=";")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stn-json", default="")
    ap.add_argument("--minskgsn-html", default="")
    ap.add_argument("--mchs-pdf", default="")
    ap.add_argument("--minenergo-html", default="")
    ap.add_argument("--extra", default=str(Path(__file__).resolve().parent.parent / "data" / "registry-extra.csv"))
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--registry", default=str(CORPUS_DEFAULT / "02-Реестр.csv"))
    ap.add_argument("--min-hits", type=int, default=2)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    registry = Path(args.registry)
    existing = load_existing(registry)
    rows = {norm_code(r["Шифр"]): r for r in existing if (r.get("Шифр") or "").strip()}
    protected = set(rows)

    added: dict[str, str] = {}
    filled = 0

    def merge(source: dict[str, dict], label: str, fill_only: bool = False) -> None:
        nonlocal filled
        for code, row in source.items():
            if code in rows:
                target = rows[code]
                for field in ("Наименование", "Введён (утверждён)", "Последнее изменение"):
                    if not (target.get(field) or "").strip() and (row.get(field) or "").strip():
                        target[field] = row[field]
                        filled += 1
                continue
            if fill_only:
                continue
            rows[code] = row
            added[code] = label

    stn: dict[str, dict] = {}
    if args.extra and Path(args.extra).exists():
        extra_rows = {norm_code(r["Шифр"]): r for r in load_existing(Path(args.extra))
                      if (r.get("Шифр") or "").strip()}
        merge(extra_rows, "registry-extra")
        print("[extra] done", file=sys.stderr, flush=True)
    if args.stn_json:
        stn, _ = stn_rows(Path(args.stn_json))
        merge(stn, "stn.by")
        print(f"[stn] {len(stn)}", file=sys.stderr, flush=True)
    if args.minskgsn_html:
        merge(minskgsn_rows(Path(args.minskgsn_html)), "minskgsn", fill_only=True)
        print("[minskgsn] done", file=sys.stderr, flush=True)
    if args.mchs_pdf:
        merge(mchs_rows(Path(args.mchs_pdf)), "МЧС")
        print("[mchs] done", file=sys.stderr, flush=True)
    if args.minenergo_html:
        merge(minenergo_rows(Path(args.minenergo_html)), "Минэнерго")
        print("[minenergo] done", file=sys.stderr, flush=True)
    merge(corpus_rows(Path(args.corpus), set(rows), args.min_hits), "проектные тексты")
    print("[corpus] done", file=sys.stderr, flush=True)
    reconciled = reconcile_statuses(rows, protected)
    print(f"[status] reconciled={reconciled}", file=sys.stderr, flush=True)

    ordered = list(existing)
    numbers = [int(r["№"]) for r in existing if (r.get("№") or "").isdigit()]
    nxt = max(numbers) + 1 if numbers else 1
    for code in sorted(added, key=lambda c: (VID.get(vid_of(c), "Я"), c)):
        row = rows[code]
        row.setdefault("№", str(nxt))
        row["№"] = str(nxt)
        nxt += 1
        ordered.append(row)

    by_vid: dict[str, int] = {}
    for r in ordered:
        by_vid[r.get("Вид") or "—"] = by_vid.get(r.get("Вид") or "—", 0) + 1

    report = [
        "# Сборка реестра ТНПА",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Записей было: {len(existing)}; добавлено: {len(added)}; "
        f"стало: {len(ordered)}; заполнено пустых полей: {filled}.",
        "",
        "По видам: " + ", ".join(f"{k}={v}" for k, v in sorted(by_vid.items())),
        "",
        "По источникам добавления:",
    ]
    src_counts: dict[str, int] = {}
    for code, label in added.items():
        src_counts[label] = src_counts.get(label, 0) + 1
    report += [f"- {k}: {v}" for k, v in sorted(src_counts.items())]
    report += ["", "Первые 40 добавленных:", ""]
    for code in sorted(added)[:40]:
        report.append(f"- {code} — {rows[code].get('Наименование') or '(без названия)'}")

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text("\n".join(report) + "\n", encoding="utf-8")

    if args.write:
        backup = registry.with_name(f"{registry.stem}.backup-{date.today():%Y%m%d}{registry.suffix}")
        if not backup.exists():
            shutil.copy2(registry, backup)
        with registry.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter=";", lineterminator="\r\n")
            w.writeheader()
            for r in ordered:
                w.writerow({c: r.get(c, "") for c in COLUMNS})

    print("\n".join(report[:8]))
    print(f"added={len(added)} total={len(ordered)} written={bool(args.write)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
