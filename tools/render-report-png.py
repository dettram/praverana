"""Пересборка снимков отчёта для лендинга из текущего прогона.

Прогон аудита → PDF → PNG первой и второй страницы; размеченный DOCX → PDF с примечаниями
(Word, `wdExportDocumentWithMarkup`) → PNG. Так кадры на лендинге не расходятся с демо.

Запуск (нужны Word и сервер на 8765):

    uv run --with pymupdf python tools/render-report-png.py \
        --project C:/Users/Public/Projects/ATLAS-TZ --out app/ui/assets/img
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import pymupdf

PAGE_WIDTH = 935  # ширина кадров на лендинге (Letter, 1210 по высоте)

WORD_EXPORT = r"""
$ErrorActionPreference = "Stop"
$docx = $args[0]
$pdf = $args[1]
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
  $doc = $word.Documents.Open($docx, $false, $true)
  # 17 = PDF, 0 = print quality, 0 = all document, 7 = document with markup (comments)
  $doc.ExportAsFixedFormat($pdf, 17, $false, 0, 0, 1, 1, 7)
  $doc.Close(0)
} finally {
  $word.Quit()
}
"""


def post(base: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def get(base: str, path: str, timeout: int = 300) -> bytes:
    return urllib.request.urlopen(base + path, timeout=timeout).read()


def run_audit(base: str, project: Path) -> str:
    job = post(base, "/api/audit", {"path": str(project), "include_text": False})["job"]
    for _ in range(180):
        data = json.loads(get(base, f"/api/audit/{job}", timeout=30))
        if data["state"] in ("done", "error"):
            if data["state"] == "error":
                raise SystemExit(f"аудит упал: {data.get('error')}")
            return job
        time.sleep(0.4)
    raise SystemExit("аудит не завершился за 72 с")


def export_marked(docx: Path, pdf: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "export.ps1"
        script.write_text(WORD_EXPORT, encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(script), str(docx), str(pdf)],
                       check=True, capture_output=True, timeout=180)


def render(pdf: Path, page_index: int, out: Path) -> tuple[int, int]:
    doc = pymupdf.open(pdf)
    page = doc[page_index]
    zoom = PAGE_WIDTH / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    pix.save(out)
    return pix.width, pix.height


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    parser.add_argument("--project", default="samples/demo-project")
    parser.add_argument("--out", default="app/ui/assets/img")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    job = run_audit(args.base, project)
    print("job", job)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pdf = tmp / "report.pdf"
        pdf.write_bytes(get(args.base, f"/api/report/{job}.pdf"))
        for index, name in ((0, "report-page.png"), (1, "report-page-2.png")):
            w, h = render(pdf, index, out / name)
            print(name, w, h)

        archive = tmp / "marked.zip"
        archive.write_bytes(get(args.base, f"/api/marked/{job}.zip"))
        with zipfile.ZipFile(archive) as zf:
            docx_name = next(n for n in zf.namelist() if n.lower().endswith(".docx"))
            marked_docx = tmp / "marked.docx"
            marked_docx.write_bytes(zf.read(docx_name))
        marked_pdf = tmp / "marked.pdf"
        export_marked(marked_docx, marked_pdf)
        w, h = render(marked_pdf, 0, out / "marked-page.png")
        print("marked-page.png", w, h)


if __name__ == "__main__":
    main()
