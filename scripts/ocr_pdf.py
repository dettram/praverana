"""OCR сканов: PDF → <имя>.ocr.txt рядом с файлом.

Движки: tesseract (по умолчанию, rus), easyocr, rapid.

  uv run --with pymupdf scripts/ocr_pdf.py --path "…/file.pdf"
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT  # noqa: E402


def tesseract_paths() -> tuple[str, str]:
    exe = os.environ.get("TESSERACT_CMD") or str(Path.home() / "tess" / "Library" / "bin" / "tesseract.exe")
    data = os.environ.get("TESSDATA_PREFIX") or str(Path.home() / "tess" / "Library" / "share" / "tessdata")
    return exe, data


def ocr_pdf(pdf: Path, out_dir: Path, dpi: int = 300, engine: str = "tess") -> tuple[int, int]:
    import pymupdf

    if engine == "tess":
        exe, data = tesseract_paths()
        env = {**os.environ, "TESSDATA_PREFIX": data}

        def recognize(img_path: Path) -> str:
            res = subprocess.run(
                [exe, str(img_path), "stdout", "-l", "rus", "--psm", "3"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
            )
            return res.stdout

    elif engine == "easy":
        import easyocr

        reader = easyocr.Reader(["ru"], gpu=False, verbose=False)

        def recognize(img_path: Path) -> str:
            return "\n".join(reader.readtext(str(img_path), detail=0, paragraph=True))
    else:
        from rapidocr_onnxruntime import RapidOCR

        rapid = RapidOCR()

        def recognize(img_path: Path) -> str:
            result, _ = rapid(str(img_path))
            return "\n".join(line[1] for line in result) if result else ""

    doc = pymupdf.open(str(pdf))
    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=dpi)
            img = Path(tmp) / f"p{i}.png"
            pix.save(str(img))
            parts.append(f"=== стр. {i} ===\n{recognize(img)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{pdf.stem}.ocr.txt"
    out.write_text("\n\n".join(parts), encoding="utf-8")
    return doc.page_count, sum(len(p) for p in parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--engine", default="tess", choices=["tess", "easy", "rapid"])
    args = ap.parse_args()

    corpus = Path(args.corpus)
    out_dir = Path(args.out_dir) if args.out_dir else corpus / "01-Нормы" / "_тексты"
    src = Path(args.path)
    files = [src] if src.is_file() else sorted(src.glob("*.pdf"))
    for f in files:
        pages, chars = ocr_pdf(f, out_dir, engine=args.engine)
        print(f"{f.name}: pages={pages} chars={chars}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
