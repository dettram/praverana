import sqlite3

import engine

SCHEMA = """
CREATE TABLE docs(id INTEGER PRIMARY KEY, rel TEXT, code TEXT, status TEXT);
CREATE TABLE clauses(doc_id INTEGER, code TEXT, clause TEXT, page INTEGER, title TEXT);
CREATE TABLE chunks(doc_id INTEGER, page INTEGER, text TEXT);
"""


def _empty_index(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.close()


def test_norm_without_index_text_does_not_warn(tmp_path, monkeypatch):
    dbfile = tmp_path / "index.sqlite"
    _empty_index(dbfile)
    monkeypatch.setattr(engine, "DB", dbfile)
    monkeypatch.setattr(engine, "CORPUS_DEFAULT", tmp_path / "corpus")

    auditor = engine.Auditor(tmp_path)
    auditor.check_norms("01-ПЗ.docx", [(1, "Ссылка: СП 5.04.01-2021, п. 99.99.99.")])

    assert not any("не найден" in finding.message for finding in auditor.scan.findings)


def test_zero_scanned_files_score_zero(tmp_path, monkeypatch):
    (tmp_path / "смета.doc").write_bytes(b"x")
    monkeypatch.setattr(engine, "DB", tmp_path / "missing.sqlite")
    monkeypatch.setattr(engine, "CORPUS_DEFAULT", tmp_path / "corpus")

    result = engine.audit(tmp_path)

    assert result["summary"]["score"] == 0.0
    assert any("текстовые документы не прочитаны" in finding["message"]
               for finding in result["findings"])


def test_where_counts_unique_files_not_occurrences(auditor):
    auditor.registry, auditor.replaced = {}, {}
    auditor.check_norms("01-ПЗ.docx", [(1, "СП 5.03.01-2020"), (2, "СП 5.03.01-2020")])
    auditor._flush_norms()

    finding = next(f for f in auditor.scan.findings if f.category == "нормы")
    assert finding.file == "01-ПЗ"
    assert "и ещё" not in finding.file


def test_where_tail_counts_files(auditor):
    auditor.registry, auditor.replaced = {}, {}
    for i in range(5):
        auditor.check_norms(f"0{i}-ПЗ.docx", [(1, "СП 5.03.01-2020")])
    auditor._flush_norms()

    finding = next(f for f in auditor.scan.findings if f.category == "нормы")
    assert finding.file == "00-ПЗ, 01-ПЗ, 02-ПЗ и ещё 2…"
