"""Проверка локальных ссылок в HTML: нет ссылки на отсутствующий файл.

  uv run python tools/check-assets.py
  uv run python tools/check-assets.py --root <папка>

Сканирует `app/ui/**/*.html`, берёт `src`, `href` и `url(...)` из inline-стилей,
пропускает внешние URL, анкоры и серверные маршруты (`/app`, `/api/...`).
Ссылки разрешаются от веб-корня `app/ui` (страницы отдаются по `/`, `/app`, `/brand`,
`/review`), поэтому `../assets/...` — это `app/ui/assets/...`, а не `app/assets/...`.
Код возврата 1 — есть отсутствующий локальный файл, 0 — чисто.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REF_RE = re.compile(r'(?:src|href)="([^"]+)"|url\(["\']?([^"\')]+)["\']?\)')
SKIP = ("http://", "https://", "//", "data:", "mailto:", "tel:", "#", "javascript:")


def references(html: str):
    for match in REF_RE.finditer(html):
        yield match.group(1) or match.group(2)


def check(root: Path) -> list[str]:
    problems: list[str] = []
    base = root / "app" / "ui"
    pages = sorted(base.rglob("*.html"))
    for page in pages:
        text = page.read_text(encoding="utf-8-sig")
        for raw in references(text):
            ref = raw.split("?", 1)[0].split("#", 1)[0].strip()
            if not ref or ref.startswith(SKIP) or ref.startswith("/"):
                continue
            while ref.startswith("../"):
                ref = ref[3:]
            target = (base / ref).resolve()
            if not target.exists():
                problems.append(f"{page.relative_to(root).as_posix()}: {raw}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Локальные ссылки в HTML существуют")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    problems = check(root)
    for problem in problems:
        print("MISSING " + problem)
    print(f"check-assets: {len(problems)} missing")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
