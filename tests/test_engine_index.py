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


def test_norms_summary_reports_full_text_availability(tmp_path, monkeypatch):
    dbfile = tmp_path / "index.sqlite"
    _empty_index(dbfile)
    conn = sqlite3.connect(dbfile)
    conn.execute("INSERT INTO docs VALUES(1, 'СП 5.03.01-2020.pdf', 'СП 5.03.01-2020', 'ok')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(engine, "DB", dbfile)
    monkeypatch.setattr(engine, "CORPUS_DEFAULT", tmp_path / "corpus")
    monkeypatch.setattr(engine, "load_registry", lambda corpus: ({}, {}))

    auditor = engine.Auditor(tmp_path)
    auditor.check_norms("01-ПЗ.docx", [
        (1, "СП 5.03.01-2020, СП 5.04.01-2021 и СНБ 2.04.02-2000.")])
    result = engine.result_dict(auditor.scan)
    by_code = {n["code"]: n for n in result["norms"]}

    assert by_code["СП 5.03.01-2020"]["has_full_text"] is True
    assert by_code["СП 5.04.01-2021"]["has_full_text"] is False
    assert by_code["СП 5.04.01-2021"]["status"] == "нет в реестре"
    assert by_code["СНБ 2.04.02-2000"]["replacement"] == "СП 2.04.04-2026"


def test_completeness_sees_skipped_cad_and_estimate_files(tmp_path, monkeypatch):
    (tmp_path / "01-ПЗ.txt").write_text("Пояснительная записка", encoding="utf-8")
    (tmp_path / "02-АР-АТЛАС.dwg").write_bytes(b"x")
    (tmp_path / "03-КР-АТЛАС.dwg").write_bytes(b"x")
    monkeypatch.setattr(engine, "DB", tmp_path / "missing.sqlite")
    monkeypatch.setattr(engine, "CORPUS_DEFAULT", tmp_path / "corpus")

    scan = engine.Auditor(tmp_path, include_text=True).run()
    message = "\n".join(f.message for f in scan.findings if f.category == "комплект")

    assert "Архитектурные" not in message
    assert "Конструкции" not in message


def test_composition_accepts_section_titles_without_codes(auditor):
    text = (
        "Календарный план строительства. Строительный генеральный план. "
        "Охрана труда. Пожарная безопасность. Охрана окружающей среды. "
        "Технико-экономические показатели."
    )
    auditor.check_composition("05-ПОС-АТЛАС.docx", [(1, text)])
    assert not any("нет обязательных разделов" in f.message for f in auditor.scan.findings)


def test_ppr_new_build_does_not_require_demolition(auditor):
    text = "Проект производства работ. В.1. Монтаж каркаса и плит перекрытия."
    auditor.check_composition("06-ППР-АТЛАС.docx", [(1, text)])
    assert not any("В.10" in f.message or "В.11" in f.message for f in auditor.scan.findings)


def test_ppr_demolition_object_requires_demolition_blocks(auditor):
    text = "Проект производства работ на снос здания. В.1. Демонтаж конструкций."
    auditor.check_composition("06-ППР-снос.docx", [(1, text)])
    assert any("В.10" in f.message for f in auditor.scan.findings)
