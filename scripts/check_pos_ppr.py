"""Проверка комплектности ПОС/ППР по составу СН 1.03.04-2020.

  uv run --with python-docx scripts/check_pos_ppr.py --kind ppr --path ppr.docx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from composition import missing_sections  # noqa: E402


def doc_text(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["pos", "ppr"])
    ap.add_argument("--path", required=True)
    args = ap.parse_args()

    path = Path(args.path)
    text = doc_text(path)
    missing = missing_sections(args.kind, text, path.name)

    print(f"Проверено разделов: база; отсутствуют: {len(missing)}")
    for m in missing:
        print("  -", m)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
