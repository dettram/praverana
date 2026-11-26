import sqlite3

import pytest

import build_index

LONG = (
    "6.3.4.1 Защитный слой бетона принят по СП 5.03.01-2020. "
    "Требования к толщине защитного слоя и его соблюдению приведены в таблице 5.1. "
    "Контроль выполняется по проектной документации и актам освидетельствования. "
    "Дополнительные требования принимаются по действующим ТНПА Республики Беларусь. "
) * 2


def _run(monkeypatch, corpus, out, *extra):
    argv = ["build_index.py", "--corpus", str(corpus), "--out", str(out),
            "--skip", "", *extra]
    monkeypatch.setattr("sys.argv", argv)
    return build_index.main()


def _rows(out):
    conn = sqlite3.connect(out)
    try:
        docs = conn.execute("SELECT rel, status, size FROM docs").fetchall()
        chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    finally:
        conn.close()
    return docs, chunks


def test_append_reindexes_no_text_file(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    target = corpus / "norm.txt"
    target.write_text("короткий текст", encoding="utf-8")
    out = tmp_path / "index.sqlite"

    _run(monkeypatch, corpus, out)
    docs, chunks = _rows(out)
    assert docs[0][1] == "no_text"
    assert chunks == 0

    target.write_text(LONG, encoding="utf-8")
    _run(monkeypatch, corpus, out, "--append")
    docs, chunks = _rows(out)
    assert len(docs) == 1
    assert docs[0][1] == "ok"
    assert docs[0][2] == len(LONG.encode("utf-8"))
    assert chunks > 0


def test_append_reindexes_changed_file(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    target = corpus / "norm.txt"
    target.write_text(LONG, encoding="utf-8")
    out = tmp_path / "index.sqlite"

    _run(monkeypatch, corpus, out)
    target.write_text(LONG + "ОБНОВЛЕНО\n", encoding="utf-8")
    _run(monkeypatch, corpus, out, "--append")

    conn = sqlite3.connect(out)
    try:
        text = "\n".join(row[0] for row in conn.execute("SELECT text FROM chunks"))
        count = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    finally:
        conn.close()
    assert count == 1
    assert "ОБНОВЛЕНО" in text


def test_append_with_clauses_builds_clause_index(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "СП 5.03.01-2020.txt").write_text(LONG, encoding="utf-8")
    out = tmp_path / "index.sqlite"

    _run(monkeypatch, corpus, out, "--append", "--with-clauses")

    conn = sqlite3.connect(out)
    try:
        rows = conn.execute("SELECT clause FROM clauses").fetchall()
    finally:
        conn.close()
    assert ("6.3.4.1",) in rows


def test_failed_file_is_retried_on_append(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    target = corpus / "norm.txt"
    target.write_text(LONG, encoding="utf-8")
    out = tmp_path / "index.sqlite"

    _run(monkeypatch, corpus, out)
    conn = sqlite3.connect(out)
    conn.execute("UPDATE docs SET status='locked'")
    conn.commit()
    conn.close()

    _run(monkeypatch, corpus, out, "--append")

    docs, chunks = _rows(out)
    assert docs[0][1] == "ok"
    assert chunks > 0
