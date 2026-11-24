"""Каталог принятых PDF + покрытие реестра. Проверяет файлы и SHA-256.

  uv run scripts/catalog.py --out-dir "…/_inbox-2026-11-23"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT, norm_code  # noqa: E402


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_registry(corpus: Path) -> dict[str, dict]:
    reg = corpus / "02-Реестр.csv"
    out: dict[str, dict] = {}
    if not reg.exists():
        return out
    with reg.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            code = norm_code(row.get("Шифр", ""))
            if code:
                out.setdefault(code, row)
    return out


def norm_key(text: str) -> str:
    return re.sub(r"[^0-9A-ZА-ЯЁ]", "", (text or "").upper())


def corpus_present(corpus: Path) -> set[str]:
    keys = []
    for p in corpus.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".txt", ".md"):
            keys.append(norm_key(p.name))
    return set(keys)


def card(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
    except Exception:  # noqa: BLE001
        return []
    out: list[str] = []

    def walk(items, depth: int = 0) -> None:
        for it in items:
            if isinstance(it, list):
                walk(it, depth + 1)
            else:
                title = getattr(it, "title", None) or str(it)
                out.append("  " * depth + title.strip())

    try:
        walk(reader.outline)
    except Exception:  # noqa: BLE001
        pass
    if not out:
        try:
            text = reader.pages[0].extract_text() or ""
        except Exception:  # noqa: BLE001
            text = ""
        out = [ln.strip() for ln in text.splitlines() if ln.strip()][:8]
    return out[:14]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    out_dir = Path(args.out_dir) if args.out_dir else corpus / "_inbox-2026-11-23"
    reg = load_registry(corpus)

    rows, problems = [], []
    for manifest in sorted(corpus.glob("_inbox-*/manifest.csv")):
        with manifest.open(encoding="utf-8-sig", newline="") as fh:
            for m in csv.DictReader(fh, delimiter=";"):
                code = norm_code(m.get("code", ""))
                f = corpus / m["file"]
                ok_file = f.exists()
                actual = sha16(f) if ok_file else ""
                sha_ok = ok_file and actual == (m.get("sha256") or "")
                if not ok_file:
                    problems.append(f"{code}: файл не найден — {m['file']}")
                elif not sha_ok:
                    problems.append(f"{code}: SHA не совпал (манифест {m.get('sha256')}, файл {actual})")
                r = reg.get(code, {})
                rows.append({
                    "code": code,
                    "title": r.get("Наименование", ""),
                    "vid": r.get("Вид", ""),
                    "status": r.get("Статус на 18.11.2026", ""),
                    "pages": m.get("pages", ""),
                    "chars": m.get("chars", ""),
                    "file": m.get("file", ""),
                    "source": m.get("source", ""),
                    "verdict": m.get("verdict", ""),
                    "sha_ok": "yes" if sha_ok else "no",
                })

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)

    have = {r["code"] for r in rows}
    file_keys = corpus_present(corpus)
    active = [c for c, r in reg.items() if (r.get("Статус на 18.11.2026") or "").startswith("действ")]
    missing = sorted(c for c in active if c not in have and not any(norm_key(c) in k for k in file_keys))
    lines = [
        "# Покрытие реестра PDF-файлами",
        "",
        f"PDF принято: {len(rows)}; активных норм в реестре: {len(active)}; "
        f"есть файл в корпусе (включая старые папки): {len(active) - len(missing)}; без файла: {len(missing)}.",
        "",
        "По видам (принято): " + ", ".join(
            f"{v}={sum(1 for r in rows if r['vid'] == v)}" for v in sorted({r["vid"] for r in rows})
        ),
        "",
        "## Без PDF (активные)",
        "",
        "| Шифр | Наименование |",
        "|---|---|",
    ]
    for c in missing[:80]:
        lines.append(f"| {c} | {(reg[c].get('Наименование') or '')[:80]} |")
    if problems:
        lines += ["", "## Проблемы", ""] + [f"- {p}" for p in problems]
    (out_dir / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    cards = ["# Карточки принятых норм", ""]
    for r in rows:
        f = corpus / r["file"]
        cards.append(f"## {r['code']} — {r['title'] or '(без названия)'}")
        cards.append(f"{r['pages']} стр.; SHA {r['sha_ok']}; `{r['file']}`")
        for item in card(f):
            cards.append(f"- {item}")
        cards.append("")
    (out_dir / "cards.md").write_text("\n".join(cards) + "\n", encoding="utf-8")

    print(f"catalog: {len(rows)} files; problems: {len(problems)}; active without pdf: {len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
