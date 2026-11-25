import pytest

from report import location_unit


@pytest.mark.parametrize("file, unit", [
    ("ПЗ.pdf", "стр."),
    ("ПЗ.PDF", "стр."),
    ("ПЗ.docx", "фрагм."),
    ("ПЗ.md", "фрагм."),
    ("ПЗ.txt", "фрагм."),
    ("—", "фрагм."),
    ("", "фрагм."),
])
def test_location_unit(file, unit):
    assert location_unit(file) == unit
