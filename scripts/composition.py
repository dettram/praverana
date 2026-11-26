"""Состав ПОС/ППР по СН 1.03.04-2020: что обязательно, что только для особых объектов.

Разделы приложений Г и В можно называть словами, без шифров «Г.7» и «В.1».
Специальные разделы (снос, линейные объекты, гидротехника, геодезия, реконструкция)
требуются только если в тексте есть соответствующий признак.
"""
from __future__ import annotations

import re

BASE_POS = ("Г.7", "Г.8", "Г.9", "Г.10", "Г.11", "Г.12")
BASE_PPR = ("В.1", "В.2", "В.3")

KEYWORDS = {
    "Г.7": ("календарный план",),
    "Г.8": ("стройгенплан", "строительный генеральный план"),
    "Г.9": ("охрана труда", "охране труда"),
    "Г.10": ("пожарн",),
    "Г.11": ("окружающей среды", "экологи"),
    "Г.12": ("технико-экономическ", "тэп"),
}

# Специальные разделы: шифр → признак объекта в тексте.
SPECIAL = {
    "В.5": ("реконструкц",),
    "В.6": ("линейн", "дорог", "трубопровод"),
    "В.7": ("гидротехн", "плотин", "канал"),
    "В.8": ("геодез",),
    "В.9": ("геодез",),
    "В.10": ("снос", "демонтаж", "ликвидац"),
    "В.11": ("снос", "демонтаж", "ликвидац"),
}


def block_present(text: str, clause: str) -> bool:
    pattern = re.compile(rf"(?<![\d.]){re.escape(clause.lower())}(?![\d])")
    if pattern.search(text):
        return True
    return any(word in text for word in KEYWORDS.get(clause, ()))


def missing_blocks(kind: str, text: str, blocks: list[dict]) -> list[str]:
    """Каких обязательных разделов не хватает; специальные — только по признаку."""
    low = text.lower()
    if kind == "pos":
        return [b["clause"] for b in blocks
                if b["clause"] in BASE_POS and not block_present(low, b["clause"])]

    has_base = any(block_present(low, clause) for clause in BASE_PPR)
    if not has_base and ("проект производства работ" in low or "организация работ" in low):
        has_base = True
    missing = [] if has_base else ["В.1 / В.2 / В.3"]
    for b in blocks:
        clause = b["clause"]
        triggers = SPECIAL.get(clause)
        if not triggers:
            continue
        if not any(trigger in low for trigger in triggers):
            continue
        if not block_present(low, clause):
            missing.append(clause)
    return missing
