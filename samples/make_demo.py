"""Демо-проект для проверки движка без корпуса норм.

  uv run --with python-docx python samples/make_demo.py --out samples/demo-project

Создаёт небольшой DOCX «пояснительной записки» с намеренными дефектами:
отменённые шифры, ссылка на пункт, которого нет, заглушки, отсутствующие разделы.
Дальше: uv run --with python-docx --with pypdf python app/engine.py --path samples/demo-project
"""
from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.shared import Pt


PARAGRAPHS = (
    "Пояснительная записка. Демонстрационный документ для проверки аудита.",
    "Проект разработан по СН 1.02.02-2023 и СН 1.03.04-2020.",
    "Нагрузки приняты по СНБ 2.04.02-2000 и СНиП 2.01.07-85 (устаревшие ссылки).",
    "Класс бетона — C25/30 по СН 5.03.01-2020 (такого шифра нет, правильно СП 5.03.01-2020).",
    "Защитный слой принят по СП 5.03.01-2020, п. 6.3.4.1.",
    "Проверка пункта, которого нет: СП 5.04.01-2021, п. 99.99.99.",
    "Шифр без года: ГОСТ 27751.",
    "Ограждающие конструкции — по проекту.",
    "Ведомость отделки: ХХХ.",
    "Место для подписи: ___.",
)


def build(out: Path) -> Path:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    doc.add_heading("Пояснительная записка (демо)", level=1)
    for text in PARAGRAPHS:
        doc.add_paragraph(text)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "ПЗ-демо.docx"
    doc.save(str(path))
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="samples/demo-project")
    args = ap.parse_args()
    path = build(Path(args.out))
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
