"""Ежемесячная сверка реестра с официальными перечнями.

Источники: minskgsn.by (перечень СН), minenergo.gov.by (перечень ТКП).
Результат: 00-Каталог/refresh-ГГГГ-ММ-ДД.md + код возврата 1, если есть расхождения.

  uv run scripts/refresh_registry.py
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CODE_RE, CORPUS_DEFAULT, norm_code  # noqa: E402

SOURCES = {
    "minskgsn": "https://www.minskgsn.by/ru/story/stroitelnye-normy-respubliki-belarus",
    "minenergo": "https://www.minenergo.gov.by/law/tnpa/",
}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.in_cell = [], [], [], False

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


def fetch(url: str) -> bytes:
    res = subprocess.run(
        ["curl.exe", "-sSL", "--ssl-no-revoke", "--max-time", "90", "-A", UA, url],
        capture_output=True, check=False,
    )
    return res.stdout


def codes_from_html(raw: bytes) -> dict[str, str]:
    text = raw.decode("utf-8", errors="replace")
    p = Table()
    p.feed(text)
    out: dict[str, str] = {}
    for row in p.rows:
        joined = " ".join(row)
        m = CODE_RE.search(joined)
        if not m:
            continue
        code = norm_code(m.group(0))
        out.setdefault(code, joined[:160])
    if not out:
        for m in CODE_RE.finditer(re.sub(r"<[^>]+>", " ", text)):
            out.setdefault(norm_code(m.group(0)), "")
    return out


def load_registry(corpus: Path) -> dict[str, dict]:
    rows = list(csv.DictReader((corpus / "02-Реестр.csv").open(encoding="utf-8-sig", newline=""), delimiter=";"))
    return {norm_code(r["Шифр"]): r for r in rows if (r.get("Шифр") or "").strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    corpus = Path(args.corpus)
    reg = load_registry(corpus)

    found: dict[str, str] = {}
    by_source: dict[str, set[str]] = {}
    for name, url in SOURCES.items():
        raw = fetch(url)
        part = codes_from_html(raw) if raw else {}
        by_source[name] = set(part)
        for code in part:
            found.setdefault(code, name)
        print(f"{name}: fetched={len(raw)} codes={len(part)}")

    new = sorted(c for c in found if c not in reg)
    # сравниваем только те виды, которые источник реально публикует
    sn_active = {c for c, r in reg.items()
                 if (r.get("Статус на 18.11.2026") or "").startswith("действ") and c.startswith("СН ")}
    gone = sorted(c for c in sn_active if c not in by_source.get("minskgsn", set()))

    lines = [
        f"# Сверка реестра — {date.today():%d.%m.%Y}",
        "",
        f"Источники: minskgsn.by, minenergo.gov.by. Найдено код(ов): {len(found)}; в реестре: {len(reg)}.",
        "",
        f"## Новые в источниках, нет в реестре ({len(new)})",
        "",
    ]
    lines += [f"- {c} ({found[c]})" for c in new[:80]] or ["—"]
    lines += ["", f"## Есть в реестре, не найдены в источниках ({len(gone)})", "",
              "Оговорка: сравниваются только СН — minskgsn публикует исключительно их; "
              "СП и ТКП в этом источнике отсутствуют по определению. Отсутствие в minskgsn "
              "не означает отмену: перечень отстаёт, статус новых СН подтверждается pravo.by.", ""]
    lines += [f"- {c}" for c in gone[:80]] or ["—"]

    out = Path(args.out) if args.out else corpus / "00-Каталог" / f"refresh-{date.today():%Y-%m-%d}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {out}; new={len(new)} missing={len(gone)}")
    return 1 if (new or gone) else 0


if __name__ == "__main__":
    raise SystemExit(main())
