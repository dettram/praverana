import sqlite3

import pytest
from clause import clause_status, docs_for_code, parse_citations

SCHEMA = """
CREATE TABLE docs(id INTEGER PRIMARY KEY, rel TEXT, code TEXT, status TEXT);
CREATE TABLE clauses(doc_id INTEGER, code TEXT, clause TEXT, page INTEGER, title TEXT);
CREATE TABLE chunks(doc_id INTEGER, page INTEGER, text TEXT);
"""


@pytest.fixture
def db(tmp_path):
    conn = sqlite3.connect(tmp_path / "index.sqlite")
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO docs VALUES(1, 'СП 5.03.01-2020.pdf', 'СП 5.03.01-2020', 'ok')")
    conn.execute("INSERT INTO chunks VALUES(1, 12, 'Защитный слой принят по п. 6.3.4.1 настоящего СП.')")
    return conn


def test_docs_for_code_does_not_mix_sn_and_sp(db):
    assert docs_for_code(db, "СП 5.03.01-2020") == [(1, "СП 5.03.01-2020.pdf")]
    assert docs_for_code(db, "СН 5.03.01-2020") == []


def test_clause_found_in_chunks(db):
    state, hits = clause_status(db, "СП 5.03.01-2020", "6.3.4.1")
    assert state == "ok"
    assert hits and hits[0]["page"] == 12


def test_missing_clause_when_text_exists(db):
    state, hits = clause_status(db, "СП 5.03.01-2020", "99.99.99")
    assert state == "no_clause"
    assert hits == []


def test_norm_without_text_is_not_a_missing_clause(db):
    state, hits = clause_status(db, "СП 5.04.01-2021", "99.99.99")
    assert state == "no_text"
    assert hits == []


def test_table_and_appendix_are_found_by_index_key(db):
    db.execute("INSERT INTO clauses VALUES(1, 'СП 5.03.01-2020', 'Таблица 5.1', 12, '')")
    db.execute("INSERT INTO clauses VALUES(1, 'СП 5.03.01-2020', 'Приложение Г', 20, '')")
    assert clause_status(db, "СП 5.03.01-2020", "Таблица 5.1")[0] == "ok"
    assert clause_status(db, "СП 5.03.01-2020", "Приложение Г")[0] == "ok"
    assert clause_status(db, "СП 5.03.01-2020", "Таблица 9.9")[0] == "no_clause"


def test_parse_citations_normalizes_table_and_appendix():
    text = "СП 5.03.01-2020, табл. 5.1; СП 5.03.01-2020, прил. Г"
    assert [c["clause"] for c in parse_citations(text)] == [
        "Таблица 5.1", "Приложение Г"]
    assert parse_citations("СП 5.03.01-2020, таблица А.1")[0]["clause"] == "Таблица А.1"
