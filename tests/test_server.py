from fastapi.testclient import TestClient

import server


def test_upload_identity_uses_root_folder():
    assert server.upload_identity(
        ["АТЛАС/ПЗ.docx", "АТЛАС/АР.pdf"]) == ("АТЛАС", ["ПЗ.docx", "АР.pdf"])
    assert server.upload_identity(["ПЗ.docx", "АР.pdf"]) == (
        "upload", ["ПЗ.docx", "АР.pdf"])


def test_run_job_uses_one_key_for_path_and_upload(tmp_path, monkeypatch):
    import history

    monkeypatch.setattr(history, "HISTORY", tmp_path / "history")
    monkeypatch.setattr(server, "audit", lambda path, include_text=False: {
        "meta": {"root": str(path), "files_scanned": 1},
        "summary": {"score": 9.0, "error": 0, "warn": 0, "info": 0},
        "findings": [], "documents": [], "errors": [],
    })

    path = tmp_path / "АТЛАС"
    path.mkdir()
    (path / "ПЗ.docx").write_bytes(b"x")
    server.JOBS["pathjob"] = {"state": "queued"}
    server.run_job("pathjob", path, False)
    path_result = server.JOBS["pathjob"]["result"]
    key = history.dataset_key(path)
    assert path_result["meta"]["history_key"] == key
    assert path_result["meta"]["source"] == "path"

    upload = tmp_path / "incoming" / "АТЛАС"
    upload.mkdir(parents=True)
    (upload / "ПЗ.docx").write_bytes(b"changed size")
    upload_key = history.dataset_key(upload, source_name="АТЛАС", names=["ПЗ.docx"])
    assert upload_key == key

    server.JOBS["upjob"] = {"state": "queued"}
    server.run_job("upjob", upload, False, upload_key, "upload")
    up_result = server.JOBS["upjob"]["result"]
    assert up_result["meta"]["source"] == "upload"
    assert any(r["source"] == "upload"
               for r in history.list_runs(str(upload), key=upload_key))


def test_download_names_are_ascii_and_keep_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "WORK", tmp_path)
    job = "jobtest"
    out = tmp_path / f"report-{job}"
    out.mkdir()
    (out / "audit-report.docx").write_bytes(b"docx")
    (out / "audit-report.pdf").write_bytes(b"pdf")
    (out / "marked").mkdir()
    (out / "marked" / "page.docx").write_bytes(b"docx")
    server.JOBS[job] = {
        "state": "done", "path": str(tmp_path), "result": {}, "error": None,
        "marked_reports": [{"comments": 1}],
    }
    client = TestClient(server.app)
    try:
        docx = client.get(f"/api/report/{job}.docx")
        assert docx.status_code == 200
        assert 'filename="praverana-report.docx"' in docx.headers["content-disposition"]
        assert docx.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        pdf = client.get(f"/api/report/{job}.pdf")
        assert pdf.status_code == 200
        assert 'filename="praverana-report.pdf"' in pdf.headers["content-disposition"]
        assert pdf.headers["content-type"] == "application/pdf"

        marked = client.get(f"/api/marked/{job}.zip")
        assert marked.status_code == 200
        assert 'filename="praverana-marked.zip"' in marked.headers["content-disposition"]
        assert marked.headers["content-type"] == "application/zip"
    finally:
        server.JOBS.pop(job, None)
