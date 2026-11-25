import pytest

from common import clean, extract_citations, norm_code, read_text, short, year_of


@pytest.mark.parametrize("raw, expected", [
    ("сн 2.01.04 - 2025*", "СН 2.01.04-2025"),
    ("СП  5.03.01 – 2020", "СП 5.03.01-2020"),
    ("  сп   5.03.01-2020  ", "СП 5.03.01-2020"),
    ("СТБ EN 1992-1-1", "СТБ EN 1992-1-1"),
    ("ГОСТ ISO 9001-2015", "ГОСТ ISO 9001-2015"),
    ("ТКП 45-2.02-315-2008", "ТКП 45-2.02-315-2008"),
    ("", ""),
])
def test_norm_code(raw, expected):
    assert norm_code(raw) == expected


@pytest.mark.parametrize("code, expected", [
    ("СП 5.03.01-2020", 2020),
    ("СН 1.02.02-99", 1999),
    ("СН 1.02.02-20", 2020),
    ("СП 5.03.01-123", None),
    ("ГОСТ 27751", None),
    ("СН 1.02.02", None),
])
def test_year_of(code, expected):
    assert year_of(code) == expected


def test_extract_citations_keeps_line_and_context():
    text = "Первая строка\nСм. СП 5.03.01-2020 и СН 1.03.04-2020, п. 7.7\n"
    citations = extract_citations(text)
    assert [c["code"] for c in citations] == ["СП 5.03.01-2020", "СН 1.03.04-2020"]
    assert citations[0]["line"] == 2
    assert "СП 5.03.01-2020" in citations[0]["context"]


def test_extract_citations_ignores_bare_clause():
    assert extract_citations("п. 6.3.4.1 и табл. 5") == []


def test_extract_citations_context_is_short():
    text = "СП 5.03.01-2020 " + "х" * 500
    assert len(extract_citations(text)[0]["context"]) <= 240


def test_read_text_utf8_and_bom(tmp_path):
    path = tmp_path / "utf8.txt"
    path.write_text("Привет", encoding="utf-8")
    assert read_text(path) == "Привет"

    bom = tmp_path / "bom.txt"
    bom.write_bytes(b"\xef\xbb\xbf" + "Привет".encode("utf-8"))
    assert read_text(bom) == "Привет"


def test_read_text_cp1251(tmp_path):
    path = tmp_path / "cp.txt"
    path.write_bytes("Привет".encode("cp1251"))
    assert read_text(path) == "Привет"


def test_clean_normalizes_spaces_and_dashes():
    assert clean("a\u00a0b\tc") == "a b c"
    assert clean("5.03.01–2020") == "5.03.01-2020"


def test_short():
    assert short("a  b\nc", 10) == "a b c"
    assert short("abcdef", 4) == "abc…"
    assert short("abc", 10) == "abc"


@pytest.mark.parametrize("raw, expected", [
    ("ПУЭ 6", "ПУЭ 6"),
    ("ПУЭ 7", "ПУЭ 7"),
    ("ТКП EN 1992-1-1-2009", "ТКП EN 1992-1-1-2009"),
    ("СТБ ISO 9001-2015", "СТБ ISO 9001-2015"),
    ("ГОСТ Р 21.1101-2013", "ГОСТ Р 21.1101-2013"),
])
def test_norm_code_prefixes(raw, expected):
    assert norm_code(raw) == expected


def test_extract_citations_recognises_new_prefixes():
    text = ("ПУЭ 6 и ТКП EN 1992-1-1-2009, СТБ ISO 9001-2015, "
            "ГОСТ Р 21.1101-2013")
    codes = [c["code"] for c in extract_citations(text)]
    assert codes == ["ПУЭ 6", "ТКП EN 1992-1-1-2009", "СТБ ISO 9001-2015",
                     "ГОСТ Р 21.1101-2013"]
