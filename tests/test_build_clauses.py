import build_clauses


def test_clause_re_captures_letter_suffix():
    m = build_clauses.CLAUSE_RE.match("6.3.4.1а Содержание защитного слоя")
    assert m and m.group(1) == "6.3.4.1а"


def test_table_re_captures_number_and_title():
    m = build_clauses.TABLE_RE.match("Таблица 5.1 Предельные отклонения")
    assert m and m.group(1) == "Таблица" and m.group(2) == "5.1"


def test_table_re_captures_appendix_letter():
    m = build_clauses.TABLE_RE.match("Приложение Г Перечень работ")
    assert m and m.group(1) == "Приложение" and m.group(2) == "Г"
