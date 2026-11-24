"""Генератор скелета ПОС/ППР по СН 1.03.04-2020 (приложения В и Г).

  uv run --with python-docx scripts/make_pos_ppr.py --kind pos --object "P324 Пляжный центр" --out pos.docx
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document
from docx.shared import Pt

SKILL = Path(__file__).resolve().parent.parent
DATA = SKILL / "data" / "pos-ppr.json"

TITLES = {
    "pos": "ПРОЕКТ ОРГАНИЗАЦИИ СТРОИТЕЛЬСТВА",
    "ppr": "ПРОЕКТ ПРОИЗВОДСТВА РАБОТ",
}
APPENDICES = {
    "pos": "Д, Е, Ж, К, Н, П",
    "ppr": "Д, Е, Ж, К, Л, М, Н",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["pos", "ppr"])
    ap.add_argument("--object", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    blocks = data[args.kind]

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    doc.add_paragraph(TITLES[args.kind]).alignment = 1
    doc.add_paragraph(args.object).alignment = 1
    doc.add_paragraph("Разработано по СН 1.03.04-2020, приложение " + ("Г" if args.kind == "pos" else "В"))
    doc.add_paragraph("")
    doc.add_paragraph("СОСТАВ ДОКУМЕНТА")
    for b in blocks:
        doc.add_paragraph(f"{b['clause']}. {b['title'][:90]}", style="List Bullet")

    for b in blocks:
        doc.add_heading(f"{b['clause']}. {b['title']}", level=2)
        for item in b["items"]:
            doc.add_paragraph(item)
        doc.add_paragraph("〔заполнить по объекту; данные — из задания на проектирование и изысканий〕")

    doc.add_heading("Приложения", level=2)
    doc.add_paragraph("Формы: " + APPENDICES[args.kind] + " (по СН 1.03.04-2020).")

    out = Path(args.out)
    doc.save(str(out))
    print(f"written: {out} ({len(blocks)} разделов)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
