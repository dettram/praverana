from fastapi.testclient import TestClient

import server


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
