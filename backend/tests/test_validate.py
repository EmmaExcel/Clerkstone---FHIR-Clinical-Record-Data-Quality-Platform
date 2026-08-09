from __future__ import annotations

from app.domain.fhir.validate import validate_payload


def _patient(**overrides) -> dict:
    base = {
        "resourceType": "Patient",
        "id": "p1",
        "name": [{"family": "Smith", "given": ["Alice"]}],
        "gender": "female",
        "birthDate": "1980-01-01",
    }
    base.update(overrides)
    return base


def test_valid_resource_has_no_issues():
    assert validate_payload(_patient()) == []


def test_missing_resource_type_is_not_supported():
    issues = validate_payload({"id": "p1"})
    assert issues and issues[0]["code"] == "not-supported"


def test_unsupported_resource_type_is_not_supported():
    issues = validate_payload({"resourceType": "TotallyMadeUp", "id": "x"})
    assert issues and issues[0]["code"] == "not-supported"


def test_invalid_structure_is_invalid():
    issues = validate_payload(_patient(gender=12345))
    assert issues and issues[0]["code"] == "invalid"


def test_bundle_validation_flags_bad_entry():
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"resource": _patient()},
            {"resource": {"resourceType": "Nope", "id": "bad"}},
        ],
    }
    issues = validate_payload(bundle)
    assert any(i["code"] == "not-supported" for i in issues)
