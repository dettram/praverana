"""Локальный сервер аудита проекта: папка → замечания → DOCX/PDF.

  uv run --with fastapi --with uvicorn --with python-docx --with pypdf --with python-multipart \
      python app/server.py

  Открыть http://127.0.0.1:8765
Всё считается на этой машине, файлы никуда не выгружаются.
"""
from __future__ import annotations

import shutil
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine import audit  # noqa: E402
from history import compare, list_runs, previous, save  # noqa: E402
from markdoc import mark_all  # noqa: E402
from report import build_docx, to_pdf  # noqa: E402

app = FastAPI(title="Праверана.by", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=str(HERE / "ui" / "assets")), name="assets")
JOBS: dict[str, dict] = {}
WORK = Path(tempfile.gettempdir()) / "stroy-audit-ui"
WORK.mkdir(parents=True, exist_ok=True)


def run_job(job_id: str, path: Path, include_text: bool) -> None:
    job = JOBS[job_id]
    job["state"] = "running"
    try:
        prev = previous(str(path), exclude_last=False)
        result = audit(path, include_text=include_text)
        result["meta"]["date"] = __import__("datetime").datetime.now().strftime("%d.%m.%Y %H:%M")
        result["history"] = {
            "runs": list_runs(str(path)),
            "previous": compare(prev, result) if prev else None,
        }
        save(result)
        job["result"] = result
        job["state"] = "done"
    except Exception as exc:  # noqa: BLE001
        job["state"] = "error"
        job["error"] = f"{type(exc).__name__}: {exc}"


def ensure_marked(job_id: str) -> tuple[Path, list[dict]]:
    """Размечает DOCX один раз на задачу; возвращает папку и статистику."""
    job = JOBS[job_id]
    out_dir = WORK / f"report-{job_id}" / "marked"
    if job.get("marked_reports") is not None:
        return out_dir, job["marked_reports"]
    reports = mark_all(job["result"], Path(job["path"]), out_dir)
    job["marked_reports"] = reports
    return out_dir, reports


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((HERE / "ui" / "landing.html").read_text(encoding="utf-8"))


@app.get("/app", response_class=HTMLResponse)
def app_page() -> HTMLResponse:
    return HTMLResponse((HERE / "ui" / "index.html").read_text(encoding="utf-8"))


@app.post("/api/audit")
def start(payload: dict) -> JSONResponse:
    raw = (payload.get("path") or "").strip().strip('"')
    if not raw:
        raise HTTPException(400, "Укажите путь к папке проекта")
    path = Path(raw)
    if not path.exists() or not path.is_dir():
        raise HTTPException(400, "Папка не найдена")
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"state": "queued", "path": str(path), "result": None, "error": None}
    threading.Thread(target=run_job, args=(job_id, path, bool(payload.get("include_text"))),
                     daemon=True).start()
    return JSONResponse({"job": job_id})


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...), include_text: bool = Form(True)) -> JSONResponse:
    if not files:
        raise HTTPException(400, "Файлы не получены")
    root = WORK / uuid.uuid4().hex[:12]
    root.mkdir(parents=True, exist_ok=True)
    for f in files:
        rel = (f.filename or "file").replace("\\", "/").lstrip("/")
        rel = "/".join(part for part in rel.split("/") if part not in ("..", "."))
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as fh:
            shutil.copyfileobj(f.file, fh)
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"state": "queued", "path": str(root), "result": None, "error": None}
    threading.Thread(target=run_job, args=(job_id, root, include_text), daemon=True).start()
    return JSONResponse({"job": job_id, "path": str(root)})


@app.get("/api/audit/{job_id}")
def status(job_id: str) -> JSONResponse:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")
    return JSONResponse({"state": job["state"], "error": job.get("error"),
                         "result": job.get("result")})


@app.get("/api/report/{job_id}.{fmt}")
def report(job_id: str, fmt: str) -> FileResponse:
    job = JOBS.get(job_id)
    if not job or job["state"] != "done":
        raise HTTPException(404, "Отчёт ещё не готов")
    if fmt not in ("docx", "pdf"):
        raise HTTPException(400, "Формат: docx или pdf")
    out_dir = WORK / f"report-{job_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    docx_path = out_dir / "audit-report.docx"
    pdf_path = out_dir / "audit-report.pdf"
    _, marked = ensure_marked(job_id)
    if not docx_path.exists():
        build_docx(job["result"], docx_path, marked=marked)
    if fmt == "docx":
        return FileResponse(str(docx_path), filename="Отчёт-аудит.docx",
                            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    if not pdf_path.exists():
        try:
            to_pdf(docx_path, pdf_path)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(500, f"Не удалось собрать PDF: {exc}. DOCX доступен.") from exc
    return FileResponse(str(pdf_path), filename="Отчёт-аудит.pdf", media_type="application/pdf")


@app.get("/api/marked/{job_id}.zip")
def marked_zip(job_id: str) -> FileResponse:
    job = JOBS.get(job_id)
    if not job or job["state"] != "done":
        raise HTTPException(404, "Разметка ещё не готова")
    out_dir, reports = ensure_marked(job_id)
    placed = [r for r in reports if r.get("comments")]
    if not placed:
        raise HTTPException(404, "В этом проекте нечего размечать (нет DOCX с замечаниями)")
    zip_path = WORK / f"report-{job_id}" / "marked.zip"
    if not zip_path.exists():
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in out_dir.rglob("*.docx"):
                zf.write(f, f.relative_to(out_dir).as_posix())
    return FileResponse(str(zip_path), filename="Размеченные-документы.zip",
                        media_type="application/zip")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
