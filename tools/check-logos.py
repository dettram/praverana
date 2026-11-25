"""Проверка файлов логотипа для экрана и печати.

Смотрит: viewBox и width/height, отсутствие живого текста, цвета. Печатает таблицу
«файл → минимум на экране → минимум в печати → фон». Код возврата 1, если файл
не прошёл проверку — тогда бренд-бук и печать расходятся.

Запуск: python tools/check-logos.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "app/ui/assets/logo"

RULES = [
    ("mark.svg", "24 px", "8 мм", "бумага", "инверсия — mark-inverse.svg"),
    ("mark-inverse.svg", "24 px", "8 мм", "тушь", "только на тёмном"),
    ("logo-horizontal.svg", "120 px по ширине", "35 мм", "бумага", "инверсия — logo-horizontal-inverse.svg"),
    ("logo-horizontal-inverse.svg", "120 px по ширине", "35 мм", "тушь", "только на тёмном"),
    ("logo-stacked.svg", "90 px по ширине", "30 мм", "бумага", "инверсия не выпускается"),
    ("logo-mono.svg", "24 px", "10 мм", "любой", "один цвет, без золота"),
    ("favicon.svg", "16–48 px", "—", "вкладка", "в печать не идёт"),
]


def check(name: str) -> list[str]:
    path = LOGO / name
    problems: list[str] = []
    if not path.exists():
        return [f"{name}: файла нет"]
    text = path.read_text(encoding="utf-8")
    if "<text" in text:
        problems.append(f"{name}: живой текст вместо кривых")
    if not re.search(r'viewBox="0 0 \d+ \d+"', text):
        problems.append(f"{name}: нет viewBox")
    if not re.search(r'width="\d+"', text) or not re.search(r'height="\d+"', text):
        problems.append(f"{name}: нет width/height")
    return problems


def main() -> int:
    problems: list[str] = []
    for name, *_ in RULES:
        problems.extend(check(name))

    print(f"{'файл':30} {'экран':18} {'печать':8} {'фон':10} примечание")
    for name, screen, print_mm, surface, note in RULES:
        print(f"{name:30} {screen:18} {print_mm:8} {surface:10} {note}")

    if problems:
        print("\nОШИБКИ:")
        for problem in problems:
            print(" -", problem)
        return 1
    print("\nвсе файлы прошли")
    return 0


if __name__ == "__main__":
    sys.exit(main())
