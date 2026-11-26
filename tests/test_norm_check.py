import pytest

from norm_check import classify, registry_date, replacement_hint

REGISTRY = {
    "СП 5.03.01-2020": {"Статус": "действует", "Заменяет / чем заменён": ""},
    "СП 5.03.01-2021": {"Статус": "не действует; заменён",
                        "Заменяет / чем заменён": "СП 5.03.01-2022"},
    "СП 5.03.01-2022": {"Статус": "не проверен", "Заменяет / чем заменён": ""},
    "СП 5.03.01-2023": {"Статус": "не вступил в силу", "Заменяет / чем заменён": ""},
    "СП 5.03.01-2024": {"Статус": "не применяется в РБ", "Заменяет / чем заменён": ""},
}


def test_snip_is_error():
    severity, message = classify("СНиП 2.01.07-85", {}, {})
    assert severity == "error"
    assert "СНиП" in message


def test_curated_outdated_has_replacement():
    severity, message = classify("СНБ 2.04.02-2000", {}, {})
    assert severity == "error"
    assert "СП 2.04.04-2026" in message


def test_no_year_is_warn():
    severity, message = classify("СП 5.03.01", {}, {})
    assert severity == "warn"
    assert "без года" in message


def test_gost_without_year_goes_to_registry():
    severity, message = classify("ГОСТ 27751", {}, {})
    assert severity == "warn"
    assert "реестр" in message


def test_active_code_is_ok():
    assert classify("СП 5.03.01-2020", REGISTRY, {}) == ("ok", "действует")


def test_cancelled_code_is_error():
    severity, message = classify("СП 5.03.01-2021", REGISTRY, {})
    assert severity == "error"
    assert "СП 5.03.01-2022" in message


def test_unconfirmed_code_is_warn():
    severity, message = classify("СП 5.03.01-2022", REGISTRY, {})
    assert severity == "warn"
    assert "не подтверждён" in message


def test_not_effective_code_is_warn():
    severity, message = classify("СП 5.03.01-2023", REGISTRY, {})
    assert severity == "warn"
    assert "не вступил" in message


def test_not_applied_code_is_error():
    severity, message = classify("СП 5.03.01-2024", REGISTRY, {})
    assert severity == "error"
    assert "не применяется" in message


def test_replaced_by_registry():
    replaced = {"СП 7.01.01-2020": {"Шифр": "СП 7.01.01-2021"}}
    severity, message = classify("СП 7.01.01-2020", {}, replaced)
    assert severity == "error"
    assert "СП 7.01.01-2021" in message


def test_unknown_code_has_hint_or_check():
    severity, message = classify("СП 9.99.99-2020", REGISTRY, {})
    assert severity == "warn"
    assert "реестр" in message


@pytest.mark.parametrize("code", ["СНиП 2.01.07-85", "СНБ 2.04.02-2000"])
def test_legacy_codes_are_never_ok(code):
    assert classify(code, REGISTRY, {})[0] == "error"


def test_dated_status_column_is_read():
    registry = {"СП 5.03.01-2020": {"Статус на 01.01.2027": "действует"}}
    assert classify("СП 5.03.01-2020", registry, {}) == ("ok", "действует")


def test_missing_status_is_warn():
    registry = {"СП 5.03.01-2020": {"Шифр": "СП 5.03.01-2020"}}
    severity, message = classify("СП 5.03.01-2020", registry, {})
    assert severity == "warn"
    assert "статус" in message.lower()


def test_unknown_status_is_warn():
    registry = {"СП 5.03.01-2020": {"Статус": "странный статус"}}
    severity, message = classify("СП 5.03.01-2020", registry, {})
    assert severity == "warn"
    assert "не распознан" in message


def test_registry_date_from_header(tmp_path):
    (tmp_path / "02-Реестр.csv").write_text(
        "Шифр;Статус на 01.01.2027\nСП 1;действует\n", encoding="utf-8")
    assert registry_date(tmp_path) == "01.01.2027"


def test_registry_date_ignores_status_narusheniy(tmp_path):
    (tmp_path / "02-Реестр.csv").write_text(
        "Шифр;Статус нарушений;Статус на 01.01.2027\nСП 1;3;действует\n",
        encoding="utf-8")
    assert registry_date(tmp_path) == "01.01.2027"


def test_harvest_status_column_is_today():
    from datetime import date

    import harvest_registry

    assert harvest_registry.STATUS_COL == f"Статус на {date.today().strftime('%d.%m.%Y')}"


def test_cancelled_status_shows_replacement_chain():
    registry = {"СНБ 2.04.02-2000": {
        "Шифр": "СНБ 2.04.02-2000",
        "Статус": "отменён",
        "Заменяет / чем заменён": "заменён на СП 2.04.04-2026",
    }}
    severity, message = classify("СНБ 2.04.02-2000", registry, {})
    assert severity == "error"
    assert "СНБ 2.04.02-2000 → СП 2.04.04-2026" in message


def test_replacement_hint_includes_introduction_date():
    hint = replacement_hint("СНБ 2.04.02-2000", {
        "Шифр": "СП 2.04.04-2026",
        "Введён (утверждён)": "01.07.2026 (пост. № 35 от 29.04.2026)",
    })
    assert hint == "СП 2.04.04-2026 (с 01.07.2026)"


def test_ambiguous_replacement_requires_check():
    registry = {"СП 1.02.01-2020": {
        "Шифр": "СП 1.02.01-2020",
        "Статус": "отменён",
        "Заменяет / чем заменён": "СП 1.02.02-2021, СП 1.02.03-2022",
    }}
    severity, message = classify("СП 1.02.01-2020", registry, {})
    assert severity == "error"
    assert "требует проверки" in message
    assert "СП 1.02.02-2021" in message and "СП 1.02.03-2022" in message
