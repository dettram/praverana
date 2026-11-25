import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for folder in (ROOT / "app", ROOT / "scripts"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import engine  # noqa: E402


@pytest.fixture
def auditor(tmp_path, monkeypatch):
    """Auditor без индекса и корпуса: только детерминированные правила."""
    monkeypatch.setattr(engine, "DB", tmp_path / "missing.sqlite")
    monkeypatch.setattr(engine, "CORPUS_DEFAULT", tmp_path / "corpus")
    return engine.Auditor(tmp_path)
