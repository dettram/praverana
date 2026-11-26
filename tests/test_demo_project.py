"""Фикстура демо-проекта: состав, дефекты и отсутствие ложных срабатываний."""

import sys
from pathlib import Path

import engine

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "samples"))

import make_demo  # noqa: E402


def test_demo_project_fixture(tmp_path, monkeypatch):
    demo = tmp_path / "demo"
    make_demo.build(demo)

    monkeypatch.setattr(engine, "DB", tmp_path / "missing.sqlite")
    monkeypatch.setattr(engine, "CORPUS_DEFAULT", tmp_path / "corpus")

    scan = engine.Auditor(demo).run()
    messages = "\n".join(f.message for f in scan.findings)

    assert scan.files_total == 8
    assert scan.files_scanned == 6

    assert "утратила силу" in messages
    assert "СНиП" in messages
    assert "«ххх»" in messages
    assert "«___»" in messages
    assert "формат .xlsx не проверяется" in messages

    # ПОС и ППР в демо полные: блоков приложений Г и В не должно недоставать.
    assert "нет обязательных разделов" not in messages

