from __future__ import annotations

from datetime import UTC, date, datetime

from app.domain.quality.rules.util import (
    codings_of,
    first_code,
    get_nhs_numbers,
    has_code,
    parse_date,
    parse_datetime,
    subject_reference,
)


def test_parse_date_full_and_datetime():
    assert parse_date("2026-01-18") == date(2026, 1, 18)
    assert parse_date("2026-01-18T16:12:00Z") == date(2026, 1, 18)


def test_parse_date_invalid():
    assert parse_date("not-a-date") is None
    assert parse_date(None) is None
    assert parse_date(12345) is None


def test_parse_datetime_z_is_tz_aware():
    assert parse_datetime("2026-01-18T16:12:00Z") == datetime(2026, 1, 18, 16, 12, tzinfo=UTC)


def test_parse_datetime_date_only():
    assert parse_datetime("2026-01-18") == datetime(2026, 1, 18)


def test_get_nhs_numbers_filters_system():
    resource = {
        "identifier": [
            {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9900000001"},
            {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "ABC"},
        ]
    }
    assert get_nhs_numbers(resource) == ["9900000001"]


def test_codings_and_has_code():
    codeable = {"coding": [{"system": "s", "code": "c1"}]}
    assert codings_of(codeable) == [{"system": "s", "code": "c1"}]
    assert codings_of(None) == []
    assert has_code({"code": codeable}, "s", "c1") is True
    assert has_code({"code": codeable}, "s", "nope") is False


def test_first_code_and_subject_reference():
    assert first_code({"coding": [{"system": "s", "code": "c"}]})["code"] == "c"
    assert first_code(None) == {}
    assert subject_reference({"subject": {"reference": "Patient/p1"}}) == "Patient/p1"
    assert subject_reference({}) is None
