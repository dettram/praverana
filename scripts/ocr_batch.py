"""Пакетный OCR сканов корпуса: sidecar <имя>.ocr.txt рядом с PDF.

  uv run --with pymupdf --with rapidocr-onnxruntime --with pillow scripts/ocr_batch.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT  # noqa: E402
from ocr_pdf import ocr_pdf  # noqa: E402

TARGETS = [
    "ГОСТ 34028-2016", "ГОСТ 5264-80", "ГОСТ 8645-68", "ГОСТ 9567-75",
    "СТБ 2255-2023", "1.020-1-83", "ГОСТ 8734-75", "ГОСТ 6402-70",
]


def main() -> int:
    corpus = Path(CORPUS_DEFAULT)
    done = 0
    for p in corpus.rglob("*.pdf"):
        if not any(t in p.name for t in TARGETS):
            continue
        side = p.with_name(f"{p.stem}.ocr.txt")
        if side.exists():
            print("skip", p.name)
            continue
        pages, chars = ocr_pdf(p, p.parent)
        print(f"{p.name}: pages={pages} chars={chars}", flush=True)
        done += 1
    print("ocr done:", done)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
