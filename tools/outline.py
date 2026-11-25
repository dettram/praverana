"""Контуры надписи логотипа из локальных woff2 (Onest 600).

Нужен, чтобы логотип не зависел от установленного шрифта: в SVG, Word, письмах и
превью ссылки надпись остаётся той же. Запуск:

    uv run --with fonttools --with brotli python tools/outline.py

Кладёт `app/ui/assets/logo/wordmark-paths.json`; `tools/logo.py` читает его при сборке.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
FONTS = REPO / "app/ui/assets/fonts"
OUT = REPO / "app/ui/assets/logo/wordmark-paths.json"

SIZE = 34.0
TRACKING = -0.8 / SIZE  # -0.8 px при 34 px
TLD_TRIM = -2.6         # кернинг пары «а.» вручную: без него точка отходит
WEIGHT = 600


def load(path: Path) -> TTFont:
    font = TTFont(path)
    if "fvar" in font:
        axes = {axis.axisTag for axis in font["fvar"].axes}
        if "wght" in axes:
            font = instantiateVariableFont(font, {"wght": WEIGHT}, inplace=False)
    return font


def main() -> None:
    cyrillic = load(FONTS / "cyrillic-wght-normal.woff2")
    latin = load(FONTS / "latin-wght-normal.woff2")
    upem = cyrillic["head"].unitsPerEm
    scale = SIZE / upem

    def glyph(char: str):
        for font in (cyrillic, latin):
            name = font.getBestCmap().get(ord(char))
            if name:
                return font, name
        raise KeyError(f"нет глифа: {char!r}")

    def place(text: str, x0: float = 0.0) -> tuple[list[dict], float]:
        x = x0
        items = []
        for char in text:
            font, name = glyph(char)
            pen = SVGPathPen(font.getGlyphSet())
            font.getGlyphSet()[name].draw(pen)
            items.append({"char": char, "d": pen.getCommands(), "x": round(x, 2)})
            x += font["hmtx"][name][0] * scale + TRACKING * SIZE
        return items, x

    main_items, width = place("праверана")
    tld_items, total = place(".by", width + TLD_TRIM)

    payload = {
        "family": "Onest",
        "weight": WEIGHT,
        "size": SIZE,
        "scale": scale,
        "tracking": TRACKING,
        "width": round(width, 2),
        "total": round(total, 2),
        "main": main_items,
        "tld": tld_items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"{OUT.name}: {len(main_items)} + {len(tld_items)} глифов, ширина {width:.1f} px, "
          f"{OUT.stat().st_size} байт")


if __name__ == "__main__":
    sys.exit(main())
