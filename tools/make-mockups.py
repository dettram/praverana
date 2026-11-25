"""Мокапы бренда из существующих файлов: визитка, шапка документа, аватар.

Без стоковых фото и 3D: только бумага, знак, типографика и образец данных.
Onest подключается локально, поэтому текст на мокапах совпадает с интерфейсом.

Запуск: uv run --with pillow python tools/make-mockups.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "app/ui"
OUT = UI / "assets/img/mockups"
FONTS = UI / "assets/fonts"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

FACE = f"""
@font-face{{font-family:"Onest";font-weight:100 900;src:url("file:///{(FONTS / 'cyrillic-wght-normal.woff2').as_posix()}") format("woff2-variations");
  unicode-range:U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116;}}
@font-face{{font-family:"Onest";font-weight:100 900;src:url("file:///{(FONTS / 'latin-wght-normal.woff2').as_posix()}") format("woff2-variations");
  unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+2000-206F,U+20AC;}}
"""

LOGO_H = (UI / "assets/logo/png/logo-horizontal.png").as_posix()
MARK = (UI / "assets/logo/png/mark.png").as_posix()
MARK_INV = (UI / "assets/logo/png/mark-inverse.png").as_posix()
WORDMARK = (UI / "assets/logo/png/logo-horizontal-inverse.png").as_posix()

CARDS = {
    "business-card": (
        1050, 583,
        f"""
        <div class="card">
          <div class="row">
            <img class="logo" src="file:///{LOGO_H}" alt="">
            <div class="role">аудит проектной документации<br>по ТНПА Беларуси</div>
          </div>
          <div class="foot">
            <div>
              <div class="name">Ирина Коваль</div>
              <div class="muted">ГИП · демо-проект</div>
            </div>
            <div class="contacts">hello@praverana.by<br>praverana.by</div>
          </div>
        </div>
        """,
    ),
    "document-header": (
        1240, 240,
        f"""
        <div class="header">
          <img class="logo" src="file:///{LOGO_H}" alt="">
          <div class="meta">
            <div class="title">Отчёт об аудите</div>
            <div class="muted">2026-АТЛ · ПОС v0.2 · 25.11.2026</div>
          </div>
        </div>
        <div class="rule"></div>
        """,
    ),
    "avatar": (
        512, 512,
        f"""
        <div class="avatar">
          <img class="mark" src="file:///{MARK_INV}" alt="">
        </div>
        """,
    ),
}

BASE_CSS = """
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{font-family:Onest,"Segoe UI",sans-serif;color:#15181A;background:#FAF9F5}
.muted{color:#5D666B}
.card{width:100%;height:100%;padding:56px 64px;display:flex;flex-direction:column;justify-content:space-between;
  background:#FAF9F5;position:relative}
.card::after{content:"";position:absolute;left:64px;right:64px;top:50%;border-top:1px solid #E4E0D6}
.row{display:flex;align-items:center;justify-content:space-between;gap:32px}
.logo{width:320px;height:auto;display:block}
.role{font-size:17px;line-height:1.45;color:#5D666B;text-align:right}
.foot{display:flex;align-items:flex-end;justify-content:space-between;gap:32px}
.name{font-size:28px;font-weight:600;letter-spacing:-.02em}
.muted{font-size:17px}
.contacts{font-size:17px;line-height:1.5;text-align:right}
.header{height:190px;padding:52px 72px 0;display:flex;align-items:flex-start;justify-content:space-between;gap:32px}
.header .logo{width:300px}
.meta{text-align:right;padding-top:8px}
.title{font-size:26px;font-weight:600;letter-spacing:-.02em}
.rule{margin:0 72px;border-top:2px solid #A97C22}
.avatar{width:100%;height:100%;background:#15181A;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px}
.avatar .mark{width:210px;height:210px}
"""


def edge() -> Path:
    if EDGE.exists():
        return EDGE
    alt = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
    if alt.exists():
        return alt
    raise SystemExit("Edge not found")


def render(name: str, width: int, height: int, body: str) -> None:
    html = (f"<!DOCTYPE html><meta charset='utf-8'><style>{FACE}{BASE_CSS}</style>{body}")
    with tempfile.TemporaryDirectory() as td:
        page = Path(td) / "page.html"
        page.write_text(html, encoding="utf-8")
        dest = OUT / f"{name}.png"
        subprocess.run([
            str(edge()), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2",
            f"--window-size={width},{height}", "--virtual-time-budget=5000",
            f"--screenshot={dest}", f"file:///{page.as_posix()}",
        ], check=True, capture_output=True, timeout=120)
        print(dest.name, dest.stat().st_size)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (width, height, body) in CARDS.items():
        render(name, width, height, body)


if __name__ == "__main__":
    main()


