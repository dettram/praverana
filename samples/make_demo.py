"""Синтетический демо-проект для аудита: 6 документов и смета XLSX.

  uv run --with python-docx --with openpyxl python samples/make_demo.py --out samples/demo-project

Данные вымышлены, заказчика нет. Дефекты заложены намеренно: отменённые шифры, пункт вне
индекса, заглушки, шифр без года, смета XLSX. ПОС и ППР полные — состав приложений Г и В
не должен давать замечаний.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook

POS_BLOCKS = 22
PPR_BLOCKS = 11


def _doc(out: Path, name: str, title: str, paragraphs: list[str]) -> None:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    doc.core_properties.title = title
    doc.core_properties.author = "Праверана.by — демо"
    doc.add_heading(title, level=1)
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(str(out / name))


def build(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    for old in (*out.glob("*.docx"), *out.glob("*.xlsx")):
        old.unlink()

    _doc(out, "01-ПЗ-АТЛАС.docx", "Пояснительная записка", [
        "Объект: жилой дом № 12 по ул. Демонстрационной (вымышленный проект).",
        "Документация разработана по СН 1.02.02-2023 и СН 1.03.04-2020.",
        "Нагрузки приняты по СНБ 2.04.02-2000 и СНиП 2.01.07-85 (устаревшие ссылки).",
        "Класс бетона — C25/30 по СН 5.03.01-2020.",
        "Проверка пункта, которого нет: СП 5.04.01-2021, п. 99.99.99.",
        "Шифр без года: ГОСТ 27751.",
        "Ограждающие конструкции — по проекту.",
        "Ведомость отделки: ХХХ.",
        "Место для подписи: ___.",
    ])
    _doc(out, "02-АР-АТЛАС.docx", "Архитектурные решения", [
        "Фасады: штукатурка, цвет по паспорту отделки.",
        "Заполнение проёмов — по ведомости.",
        "Пожарные требования — по СН 2.02.01-2019.",
    ])
    _doc(out, "03-КР-АТЛАС.docx", "Конструктивные решения", [
        "Фундамент — монолитная плита.",
        "Класс бетона C25/30 по СН 5.03.01-2020.",
        "Армирование — по спецификации.",
        "Сейсмичность района — 6 баллов, по СН 2.01.01-2022.",
    ])
    _doc(out, "04-ИОС-АТЛАС.docx", "Инженерное оборудование", [
        "Отопление и вентиляция — по СН 4.02.03-2019.",
        "Водоснабжение и канализация — по СН 4.01.02-2019.",
        "Электроснабжение — по ТКП 45-4.04-149-2009.",
    ])

    pos = "; ".join(f"Г.{i}" for i in range(1, POS_BLOCKS + 1))
    _doc(out, "05-ПОС-АТЛАС.docx", "Проект организации строительства", [
        "Проект организации строительства разработан по СН 1.03.04-2020.",
        "Документ не может служить основанием для производства работ.",
        "Состав по приложению Г: " + pos + ".",
        "Очерёдность строительства: подготовительный период, основной, отделка.",
    ])

    ppr = "; ".join(f"В.{i}" for i in range(1, PPR_BLOCKS + 1))
    _doc(out, "06-ППР-АТЛАС.docx", "Проект производства работ", [
        "Проект производства работ на монтаж конструкций.",
        "Состав по приложению В: " + ppr + ".",
        "Грузоподъёмность крана — по расчёту.",
    ])

    book = Workbook()
    sheet = book.active
    sheet.title = "Смета"
    sheet.append(["№", "Наименование", "Ед.", "Кол-во"])
    sheet.append([1, "Устройство фундамента", "м3", 120])
    sheet.append([2, "Монтаж каркаса", "т", 36])
    book.save(str(out / "07-Смета-АТЛАС.xlsx"))

    (out / "README.md").write_text(
        "# Демо-проект\n\n"
        "Синтетический комплект для аудита: ПЗ, АР, КР, ИОС, ПОС, ППР и смета XLSX.\n"
        "Данные вымышлены, заказчика и реальных объектов нет.\n\n"
        "Заложенные дефекты:\n"
        "- СНБ 2.04.02-2000 — отменён, замена СП 2.04.04-2026;\n"
        "- СНиП 2.01.07-85 — в РБ не применяются;\n"
        "- СП 5.04.01-2021, п. 99.99.99 — пункта нет в индексе;\n"
        "- ГОСТ 27751 без года — статус не определить;\n"
        "- заглушки ХХХ и ___;\n"
        "- смета XLSX — формат не проверяется.\n",
        encoding="utf-8",
    )
    return sorted(out.iterdir())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="samples/demo-project")
    args = ap.parse_args()
    files = build(Path(args.out))
    print("demo:", [p.name for p in files])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
