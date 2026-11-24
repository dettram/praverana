"""Извлечение приложений В (ППР) и Г (ПОС) из СН 1.03.04-2020 в структурированный вид.

  uv run --with python-docx scripts/extract_pos_ppr.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent


def section_text(text: str, start_marker: str, end_markers: tuple[str, ...]) -> str:
    positions = [i for i in range(len(text)) if text.startswith(start_marker, i)]
    if not positions:
        return ""
    start = positions[-1]
    ends = [text.find(m, start + len(start_marker)) for m in end_markers]
    ends = [e for e in ends if e > start]
    end = min(ends) if ends else len(text)
    return text[start:end]


def parse_items(block: str, prefix: str) -> list[dict]:
    # гарантируем, что каждый пункт начинается с новой строки (в DOCX бывает склейка)
    block = re.sub(rf"(?<![.\d])({prefix}\.\d+(?:\.\d+)*)\s+", r"\n\1 ", block)
    items: list[dict] = []
    current = None
    buf: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(rf"^({prefix}\.\d+(?:\.\d+)*)\s+(.*)$", line)
        if m:
            current = {"clause": m.group(1), "title": m.group(2).strip(), "items": []}
            items.append(current)
            buf = []
            continue
        if current is None:
            continue
        buf.append(line)
        if line.endswith((";", ".")):
            item = re.sub(r"\s+", " ", " ".join(buf)).rstrip(";")
            if item:
                current["items"].append(item)
            buf = []
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    args = ap.parse_args()
    corpus = Path(args.corpus)

    docx = next((corpus / "01-Нормы" / "СН").glob("СН 1.03.04-2020*.docx"))
    from docx import Document

    text = "\n".join(p.text for p in Document(str(docx)).paragraphs if p.text.strip())

    vpr = section_text(text, "Приложение В", ("Приложение Г", "Приложение Д"))
    pos = section_text(text, "Приложение Г", ("Приложение Д", "Приложение Е"))

    data = {
        "source": "СН 1.03.04-2020, приложения В и Г",
        "ppr": parse_items(vpr, "В"),
        "pos": parse_items(pos, "Г"),
    }

    (SKILL / "data").mkdir(exist_ok=True)
    (SKILL / "data" / "pos-ppr.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Состав ПОС и ППР (СН 1.03.04-2020)", "",
          "Источник: `01-Нормы/СН/СН 1.03.04-2020 — Организация строительного производства`.",
          "Пункты 7.7 (ПОС → прил. Г) и 7.8.9 (ППР → прил. В).", ""]
    for key, title in (("pos", "ПОС — приложение Г"), ("ppr", "ППР — приложение В")):
        md += [f"## {title}", ""]
        for block in data[key]:
            md.append(f"### {block['clause']}. {block['title']}")
            md += [f"- {it}" for it in block["items"]]
            md.append("")
    (SKILL / "references" / "pos-ppr-composition.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"ppr={len(data['ppr'])} pos={len(data['pos'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
