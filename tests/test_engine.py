import pytest

import engine
from engine import Finding, Scan, pair_citations, result_dict


@pytest.mark.parametrize("line, expected", [
    ("СП 5.03.01-2020, п. 6.3.4.1", [("СП 5.03.01-2020", "6.3.4.1")]),
    ("СП 5.04.01-2021, п. 5.04.01", []),
    ("СП 5.03.01-2020, п. 7", []),
    ("СП 5.03.01-2020 и СН 1.03.04-2020, п. 7.7", [("СН 1.03.04-2020", "7.7")]),
])
def test_pair_citations(line, expected):
    assert pair_citations(line) == expected


def test_pair_citations_respects_80_chars():
    line = "СП 5.03.01-2020" + " " * 81 + "п. 6.3.4.1"
    assert pair_citations(line) == []


def test_completeness_all_groups(auditor):
    auditor.check_completeness(["ПЗ.docx", "АР-01.docx", "КР-01.docx", "ИОС-01.docx",
                                "ПОС-01.docx", "ППР-01.docx", "Смета.xlsx"])
    assert auditor.scan.findings == []


def test_completeness_missing_groups(auditor):
    auditor.check_completeness([])
    assert len(auditor.scan.findings) == 1
    finding = auditor.scan.findings[0]
    assert finding.severity == "warn"
    assert finding.category == "комплект"
    for title in ("ПЗ", "АР", "КР/КЖ/КМ", "ИОС", "ПОС", "ППР", "Сметы"):
        assert title in finding.message


def test_composition_ppr_missing_blocks(auditor):
    auditor.check_composition("ППР-01.docx", [(1, "Проект производства работ")])
    assert any("приложения В" in f.message for f in auditor.scan.findings)


def test_composition_km_is_info(auditor):
    auditor.check_composition("ППР-КМ-01.docx", [(1, "монтаж")])
    assert len(auditor.scan.findings) == 1
    assert auditor.scan.findings[0].severity == "info"
    assert "В.2" in auditor.scan.findings[0].message


def test_composition_sgp_skipped(auditor):
    auditor.check_composition("СГП-01.docx", [(1, "стройгенплан")])
    assert auditor.scan.findings == []


def test_composition_pos_disclaimer(auditor):
    auditor.check_composition("ПОС-01.docx", [(1, "Проект организации строительства")])
    assert any("не может служить основанием" in f.message
               for f in auditor.scan.findings)


def test_placeholders_hard_and_soft(auditor):
    auditor.check_placeholders("x.docx", [(1, "ХХХ ___ заполнить по проекту")])
    hard = [f for f in auditor.scan.findings if f.severity == "warn"]
    soft = [f for f in auditor.scan.findings if f.severity == "info"]
    assert len(hard) == 3
    assert len(soft) == 1


def test_add_deduplicates(auditor):
    finding = Finding("warn", "заглушки", "x.docx", 1, "текст")
    auditor.add(finding)
    auditor.add(finding)
    assert len(auditor.scan.findings) == 1


def test_norms_deduplicate_by_code(auditor):
    auditor.registry, auditor.replaced = {}, {}
    auditor.check_norms("x.docx", [(1, "СНБ 2.04.02-2000"), (2, "СНБ 2.04.02-2000")])
    auditor._flush_norms()
    assert len(auditor.scan.findings) == 1
    assert "2 раз" in auditor.scan.findings[0].message


def test_norms_truncated_code_skipped(auditor):
    auditor.registry, auditor.replaced = {}, {}
    auditor.check_norms("x.docx", [(1, "СП 5.03.01")])
    auditor._flush_norms()
    assert auditor.scan.findings == []


def test_norms_active_code_skipped(auditor):
    auditor.registry = {"СП 5.03.01-2020": {"Статус на 18.11.2026": "действует"}}
    auditor.replaced = {}
    auditor.check_norms("x.docx", [(1, "СП 5.03.01-2020")])
    auditor._flush_norms()
    assert auditor.scan.findings == []


def test_unsupported_formats_are_not_scans(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "DB", tmp_path / "missing.sqlite")
    monkeypatch.setattr(engine, "CORPUS_DEFAULT", tmp_path / "corpus")
    (tmp_path / "a.xlsx").write_bytes(b"x")
    (tmp_path / "b.doc").write_bytes(b"x")

    scan = engine.Auditor(tmp_path).run()
    messages = [f.message for f in scan.findings]
    assert not any("скан без OCR" in m for m in messages)
    assert any(".xlsx" in m and "не проверяется" in m for m in messages)
    assert any(".doc" in m and "не проверяется" in m for m in messages)


def _scan(*severities):
    return Scan(root="x", files_scanned=1,
                findings=[Finding(s, "x", "f", None, "m") for s in severities])


def test_score_clean():
    assert result_dict(_scan())["summary"]["score"] == 10.0


def test_score_one_error():
    assert result_dict(_scan("error"))["summary"]["score"] == 9.0


def test_score_error_cap():
    assert result_dict(_scan(*["error"] * 7))["summary"]["score"] == 4.0


def test_score_warn_cap():
    assert result_dict(_scan(*["warn"] * 20))["summary"]["score"] == 7.0


def test_score_info_cap():
    assert result_dict(_scan(*["info"] * 30))["summary"]["score"] == 9.0
