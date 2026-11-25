"""Праверана.by — знак и логотип.

Знак: квадратная плашка-штамп с вырезанной буквой П (Праверана). Без галочки,
без орнамента и без золота в самом знаке: золото живёт в надписи `.by`.

Одна геометрия даёт все файлы: mark, инверсию, монохром, favicon, горизонтальный
и вертикальный логотип. Надпись — контуры из wordmark-paths.json (tools/outline.py),
поэтому шрифт Onest для логотипа не требуется.

Запуск: python tools/logo.py <out-dir> [--preview]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

INK = "#15181a"
PAPER = "#faf9f5"
GOLD_TEXT = "#8a5f14"
GOLD_ON_DARK = "#d9a441"

WORDMARK = Path(__file__).resolve().parent.parent / "app/ui/assets/logo/wordmark-paths.json"

# --- геометрия -------------------------------------------------------------

PLATE = {"x": 12, "y": 12, "size": 40, "radius": 2}
LETTER = {"x": 19, "y": 18, "width": 26, "bar": 7, "stem": 7, "height": 28}


def wordmark_paths():
    try:
        return json.loads(WORDMARK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def plate(color: str) -> str:
    p = PLATE
    return (f'<rect x="{p["x"]}" y="{p["y"]}" width="{p["size"]}" height="{p["size"]}" '
            f'rx="{p["radius"]}" fill="{color}"/>')


def letter(color: str) -> str:
    """Буква П тремя прямоугольниками: перекладина перекрывает стойки."""
    l = LETTER
    x, y, w, bar, stem, h = l["x"], l["y"], l["width"], l["bar"], l["stem"], l["height"]
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{bar}" fill="{color}"/>'
            f'<rect x="{x}" y="{y}" width="{stem}" height="{h}" fill="{color}"/>'
            f'<rect x="{x + w - stem}" y="{y}" width="{stem}" height="{h}" fill="{color}"/>')


def mark_body(ink: str, background: str) -> str:
    return plate(ink) + letter(background)


def svg_wrap(body: str, viewbox: str, label: str, title: str) -> str:
    _, _, w, h = viewbox.split()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{viewbox}" '
            f'role="img" aria-label="{label}"><title>{title}</title>{body}</svg>')


def mark_svg(inverse: bool = False) -> str:
    ink, background = (PAPER, INK) if inverse else (INK, PAPER)
    return svg_wrap(mark_body(ink, background), "0 0 64 64",
                    "Праверана.by — знак",
                    "Знак Праверана.by: штамп с буквой П")


def favicon_svg() -> str:
    """Бумажная плашка, чтобы знак был виден и на тёмной вкладке."""
    body = (f'<rect width="64" height="64" rx="14" fill="{PAPER}"/>'
            '<g transform="translate(32 32) scale(1.16) translate(-32 -32)">'
            + mark_body(INK, PAPER) + "</g>")
    return svg_wrap(body, "0 0 64 64", "Праверана.by", "Знак Праверана.by для вкладки")


def mono_svg() -> str:
    return svg_wrap(mark_body(INK, PAPER), "0 0 64 64",
                    "Праверана.by — монохромный знак",
                    "Знак Праверана.by в один цвет")


def wordmark(fill: str, tld: str, size: float = 34.0, x: float = 80.0,
             baseline: float = 43.0, middle: bool = False) -> str:
    """Надпись контурами из wordmark-paths.json; без файла — запасной живой текст."""
    data = wordmark_paths()
    if not data:
        anchor = "middle" if middle else "start"
        return (f'<text x="{x}" y="{baseline}" text-anchor="{anchor}" '
                f'font-family="Onest, \'Segoe UI\', Arial, sans-serif" '
                f'font-size="{size:g}" font-weight="600" letter-spacing="-0.8" fill="{fill}">'
                f'праверана<tspan fill="{tld}">.by</tspan></text>')
    factor = size / data["size"]
    scale = data["scale"] * factor
    width = data.get("total", data["width"]) * factor
    x0 = x - width / 2 if middle else x

    def glyphs(items, color: str) -> str:
        return "".join(
            f'<path d="{item["d"]}" transform="translate({item["x"]} 0) '
            f'scale({scale:.6f} -{scale:.6f})" fill="{color}"/>'
            for item in items
        )

    return (f'<g transform="translate({x0:g} {baseline:g}) scale({factor:.6f})">'
            f'{glyphs(data["main"], fill)}{glyphs(data["tld"], tld)}</g>')


def horizontal_svg(inverse: bool = False) -> str:
    ink, background = (PAPER, INK) if inverse else (INK, PAPER)
    fill = PAPER if inverse else INK
    tld = GOLD_ON_DARK if inverse else GOLD_TEXT
    body = mark_body(ink, background) + wordmark(fill, tld)
    return svg_wrap(body, "0 0 372 64", "Праверана.by",
                    "Праверана.by — горизонтальный логотип")


def stacked_svg() -> str:
    body = (f'<g transform="translate(64 2)">' + mark_body(INK, PAPER) + "</g>"
            + wordmark(INK, GOLD_TEXT, size=26, x=96, baseline=104, middle=True))
    return svg_wrap(body, "0 0 192 128", "Праверана.by",
                    "Праверана.by — вертикальный логотип")


FILES = {
    "mark.svg": mark_svg,
    "mark-inverse.svg": lambda: mark_svg(inverse=True),
    "logo-horizontal.svg": horizontal_svg,
    "logo-horizontal-inverse.svg": lambda: horizontal_svg(inverse=True),
    "logo-stacked.svg": stacked_svg,
    "logo-mono.svg": mono_svg,
    "favicon.svg": favicon_svg,
}


def write_all(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, build in FILES.items():
        text = build()
        (out / name).write_text(text, encoding="utf-8")
        print(f"{name}: {len(text)} bytes")


def preview(out: Path) -> None:
    mark = mark_body(INK, PAPER)
    inverse = mark_body(PAPER, INK)
    mono = mark_body(INK, PAPER)
    fav = f'<rect width="64" height="64" rx="14" fill="{PAPER}"/>' + mark
    sizes = "".join(
        f'<div class="cell"><svg viewBox="0 0 64 64" width="{s}" height="{s}">{mark}</svg>'
        f"<span>{s}</span></div>" for s in (16, 20, 24, 32, 48, 96)
    )
    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Знак Праверана.by</title>
<style>
body{{margin:0;padding:32px;background:#fff;font:14px/1.5 "Segoe UI",Arial,sans-serif;color:#15181a}}
h1{{font-size:18px;margin:0 0 20px}} h2{{font-size:13px;color:#5d666b;margin:24px 0 10px}}
.row{{display:flex;align-items:flex-end;gap:26px}}
.cell{{display:flex;flex-direction:column;align-items:center;gap:8px}}
.cell span{{font:11px Consolas,monospace;color:#8a8f94}}
header{{display:flex;align-items:center;gap:10px;border-bottom:1px solid #e4e0d6;padding:0 0 14px;font:600 20px "Segoe UI"}}
header i{{font-style:normal;color:#8a5f14}}
footer{{display:flex;align-items:center;gap:10px;background:#15181a;color:#faf9f5;padding:14px 18px;border-radius:8px;font:600 20px "Segoe UI";margin-top:14px}}
footer i{{font-style:normal;color:#d9a441}}
.card{{border:1px solid #e4e0d6;border-radius:10px;padding:18px;display:inline-flex;align-items:center;gap:14px}}
.card .l{{font-size:12px;color:#5d666b;width:110px}}
.mono{{background:#15181a;padding:10px;border-radius:8px;display:inline-flex}}
</style></head><body>
<h1>Знак: штамп-П</h1>
<div class="row">{sizes}
  <div class="cell"><div class="mono"><svg viewBox="0 0 64 64" width="96" height="96">{inverse}</svg></div><span>96 · на тушь</span></div>
  <div class="cell"><svg viewBox="0 0 64 64" width="32" height="32">{fav}</svg><span>favicon</span></div>
</div>
<h2>В шапке</h2>
<header><svg viewBox="0 0 64 64" width="30" height="30">{mark}</svg>праверана<i>.by</i></header>
<h2>На тёмной плашке</h2>
<footer><svg viewBox="0 0 64 64" width="34" height="34">{inverse}</svg>праверана<i>.by</i></footer>
<h2>Монохром</h2>
<div class="card"><div class="l">Один цвет, печать</div>
<svg viewBox="0 0 64 64" width="64" height="64">{mono}</svg></div>
</body></html>"""
    (out / "logo-preview.html").write_text(html, encoding="utf-8")
    print("preview: logo-preview.html")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("app/ui/assets/logo")
    write_all(target)
    if "--preview" in sys.argv:
        preview(Path(r"C:\Users\g.macuev\AppData\Local\Temp\harvest"))
