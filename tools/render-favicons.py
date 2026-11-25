"""Набор иконок приложения: PNG, ICO, mask-icon и manifest.

Табличные иконки — из существующего favicon.svg (бумажная плашка). Для iOS и Android —
полноразмерная бумажная подложка с запасом под маску, иначе система обрежет знак.

Запуск:

    uv run --with pillow python tools/render-favicons.py
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "app/ui"
LOGO = UI / "assets/logo"
OUT = UI / "assets/icons"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

TAB_SIZES = (16, 32, 48)
MASK_SIZES = (180, 192, 512)

FULL_BLEED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" fill="#faf9f5"/>
<g transform="translate(32 32) scale(0.86) translate(-32 -32)">
{mark}
</g></svg>"""

PINNED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<path fill="#000" fill-rule="evenodd"
  d="M12 12 H52 V52 H12 Z M19 18 H45 V46 H38 V25 H26 V46 H19 Z"/>
</svg>"""

MANIFEST = {
    "name": "Праверана.by — аудит проектной документации",
    "short_name": "Праверана",
    "description": "Локальный аудит проектной документации по ТНПА Республики Беларусь.",
    "lang": "ru",
    "start_url": "/app",
    "scope": "/",
    "display": "standalone",
    "background_color": "#FAF9F5",
    "theme_color": "#FAF9F5",
    "icons": [
        {"src": "/assets/icons/favicon-192.png", "sizes": "192x192", "type": "image/png",
         "purpose": "any maskable"},
        {"src": "/assets/icons/favicon-512.png", "sizes": "512x512", "type": "image/png",
         "purpose": "any maskable"},
    ],
}


def edge() -> Path:
    if EDGE.exists():
        return EDGE
    alt = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
    if alt.exists():
        return alt
    raise SystemExit("Edge not found")


def render(source: Path | str, size: int, dest: Path) -> None:
    """source — путь к SVG или готовая SVG-строка."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if isinstance(source, str):
            svg = td / "pic.svg"
            svg.write_text(source, encoding="utf-8")
        else:
            svg = source
        html = td / "pic.html"
        html.write_text(
            "<!DOCTYPE html><meta charset='utf-8'><style>html,body{margin:0;background:transparent}"
            f"img{{display:block}}</style><img src='file:///{svg.as_posix()}' width='{size}' height='{size}'>",
            encoding="utf-8",
        )
        subprocess.run(
            [str(edge()), "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--default-background-color=00000000", "--force-device-scale-factor=1",
             f"--window-size={size},{size}", "--virtual-time-budget=4000",
             f"--screenshot={dest}", f"file:///{html.as_posix()}"],
            check=True, capture_output=True, timeout=120,
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mark = (LOGO / "mark.svg").read_text(encoding="utf-8")
    inner = mark.split(">", 1)[1].rsplit("</svg>", 1)[0]
    full = FULL_BLEED.format(mark=inner)

    for size in TAB_SIZES:
        dest = OUT / f"favicon-{size}.png"
        render(LOGO / "favicon.svg", size, dest)
        print(dest.name, Image.open(dest).size)

    for size in MASK_SIZES:
        name = "apple-touch-icon-180.png" if size == 180 else f"favicon-{size}.png"
        dest = OUT / name
        render(full, size, dest)
        print(dest.name, Image.open(dest).size)

    ico = OUT / "favicon.ico"
    Image.open(OUT / "favicon-48.png").save(ico, sizes=[(16, 16), (32, 32), (48, 48)])
    print("favicon.ico", Image.open(ico).size)

    (OUT / "safari-pinned-tab.svg").write_text(PINNED, encoding="utf-8")
    (UI / "assets/manifest.webmanifest").write_text(
        json.dumps(MANIFEST, ensure_ascii=False, indent=2), encoding="utf-8")
    print("safari-pinned-tab.svg, manifest.webmanifest")


if __name__ == "__main__":
    main()

