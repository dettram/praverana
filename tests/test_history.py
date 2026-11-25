import json
from pathlib import Path

import history


def finding(message="текст", category="нормы", norm="СП 5.03.01-2020",
            severity="warn", file="x.docx"):
    return {"severity": severity, "category": category, "file": file,
            "message": message, "norm": norm}


def run(root="C:/proj", files=1, score=8.0, error=0, warn=0, info=0,
        findings=None, date=None):
    meta = {"root": root, "files_scanned": files}
    if date is not None:
        meta["date"] = date
    return {
        "meta": meta,
        "summary": {"score": score, "error": error, "warn": warn, "info": info},
        "findings": findings or [],
    }


def write_run(tmp_path: Path, root: str, stamp: str, data: dict) -> Path:
    key = history._key(root)
    path = tmp_path / f"{stamp}-{key}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_key_is_stable_and_case_insensitive():
    assert history._key("C:/Proj") == history._key("c:/proj")
    assert history._key("C:/a") != history._key("C:/b")
    assert len(history._key("C:/a")) == 8


def test_norm_text_strips_counter_and_spaces():
    assert history._norm_text("Нет блоков (встречается 2 раз)") == "нет блоков"
    assert history._norm_text("  A\n B  ") == "a b"
    assert history._norm_text("") == ""


def test_finding_key_ignores_counter():
    one = history.finding_key(finding("нет блоков (встречается 1 раз)"))
    three = history.finding_key(finding("нет блоков (встречается 3 раз)"))
    assert one == three


def test_save_writes_json(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path / "runs")
    data = run()
    path = history.save(data)
    assert path.exists()
    assert path.name.endswith(f"-{history._key('C:/proj')}.json")
    assert json.loads(path.read_text(encoding="utf-8")) == data


def test_previous_returns_older_run(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    write_run(tmp_path, "C:/proj", "20260101-120000", run(score=7.0))
    write_run(tmp_path, "C:/proj", "20260101-130000", run(score=8.0))

    old = history.previous("C:/proj")
    latest = history.previous("C:/proj", exclude_last=False)
    assert old["summary"]["score"] == 7.0
    assert latest["summary"]["score"] == 8.0


def test_previous_without_runs_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    assert history.previous("C:/none") is None


def test_previous_skips_corrupt(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    write_run(tmp_path, "C:/proj", "20260101-100000", run(score=6.0))
    (tmp_path / f"20260101-110000-{history._key('C:/proj')}.json").write_text("{", encoding="utf-8")
    write_run(tmp_path, "C:/proj", "20260101-120000", run(score=9.0))

    assert history.previous("C:/proj")["summary"]["score"] == 6.0


def test_list_runs_order_limit_and_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    write_run(tmp_path, "C:/proj", "20260101-100000", run(score=7.0, error=1, warn=2, info=3))
    write_run(tmp_path, "C:/proj", "20260101-110000", run(score=8.0, error=2, warn=3, info=4))
    write_run(tmp_path, "C:/proj", "20260101-120000", run(score=9.0, error=3, warn=4, info=5))

    runs = history.list_runs("C:/proj")
    assert [r["score"] for r in runs] == [9.0, 8.0, 7.0]
    assert history.list_runs("C:/proj", limit=1)[0]["score"] == 9.0
    first = runs[0]
    assert first["error"] == 3
    assert first["warn"] == 4
    assert first["info"] == 5
    assert first["files"] == 1
    assert first["file"].endswith(".json")
    assert first["date"]


def test_list_runs_skips_corrupt(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY", tmp_path)
    write_run(tmp_path, "C:/proj", "20260101-100000", run(score=7.0))
    (tmp_path / f"20260101-110000-{history._key('C:/proj')}.json").write_text("not json", encoding="utf-8")

    runs = history.list_runs("C:/proj")
    assert len(runs) == 1
    assert runs[0]["score"] == 7.0


def test_compare_identical(tmp_path):
    item = finding()
    result = history.compare(run(findings=[item]), run(findings=[item]))
    assert result["fixed_count"] == 0
    assert result["added_count"] == 0
    assert result["delta"] == {"score": 0.0, "error": 0, "warn": 0, "info": 0}
    assert result["scope_changed"] is False


def test_compare_fixed_and_added():
    old = run(findings=[finding("старое"), finding("общее")])
    new = run(findings=[finding("общее"), finding("новое")])
    result = history.compare(old, new)
    assert result["fixed_count"] == 1
    assert result["added_count"] == 1
    assert result["fixed"][0]["message"] == "старое"
    assert result["added"][0]["message"] == "новое"


def test_compare_counter_change_is_not_new():
    old = run(findings=[finding("нет блоков (встречается 1 раз)")])
    new = run(findings=[finding("нет блоков (встречается 3 раз)")])
    result = history.compare(old, new)
    assert result["fixed_count"] == 0
    assert result["added_count"] == 0


def test_compare_scope_changed_and_delta():
    old = run(files=2, score=7.0, error=1, warn=2, info=3)
    new = run(files=3, score=8.5, error=0, warn=1, info=2)
    result = history.compare(old, new)
    assert result["scope_changed"] is True
    assert result["files_old"] == 2
    assert result["files_new"] == 3
    assert result["delta"] == {"score": 1.5, "error": -1, "warn": -1, "info": -1}
    assert result["old_date"] == ""


def test_compare_caps_lists_at_40():
    old = run(findings=[finding(f"старое {i}", norm=f"N{i}") for i in range(45)])
    new = run(findings=[])
    result = history.compare(old, new)
    assert result["fixed_count"] == 45
    assert len(result["fixed"]) == 40
    assert result["added_count"] == 0


def test_compare_keeps_date():
    result = history.compare(run(date="01.01.2026"), run(date="02.01.2026"))
    assert result["old_date"] == "01.01.2026"
