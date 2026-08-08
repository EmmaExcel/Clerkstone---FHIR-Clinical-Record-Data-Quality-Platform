from __future__ import annotations

import pytest
from app.domain.fhir.nhs import is_valid, make_valid_nhs_number
from app.domain.quality.rules.base import RuleContext
from app.domain.quality.rules.registry import get_rule_map

RULES = get_rule_map()


def _ctx(resource: dict, patient: dict | None = None, reference_exists=None, terminology=None):
    return RuleContext(
        resource=resource,
        resource_type=resource.get("resourceType"),
        patient=patient,
        reference_exists=reference_exists or (lambda _: True),
        terminology=terminology,
    )


def _patient(**overrides) -> dict:
    base = {
        "resourceType": "Patient",
        "id": "p1",
        "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9900000001"}],
        "name": [{"family": "Smith", "given": ["Alice"]}],
        "gender": "female",
        "birthDate": "1980-01-01",
    }
    base.update(overrides)
    return base


def _observation(code: str = "271649006", value: float = 120.0, **overrides) -> dict:
    base = {
        "resourceType": "Observation",
        "id": "o1",
        "status": "final",
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": code}]},
        "subject": {"reference": "Patient/p1"},
        "valueQuantity": {"value": value, "unit": "mm[Hg]"},
    }
    base.update(overrides)
    return base


class TestNhsNumber:
    def test_check_digit_valid(self):
        n = make_valid_nhs_number("990000001")
        assert is_valid(n)

    def test_check_digit_invalid(self):
        valid = make_valid_nhs_number("990000001")
        bad = valid[:-1] + str((int(valid[-1]) + 1) % 10)
        assert not is_valid(bad)

    def test_invalid_check_digit_rule_fires(self):
        patient = _patient(identifier=[{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9900000019"}])
        findings = RULES["IDENT-003"].evaluate(_ctx(patient))
        assert findings

    def test_valid_check_digit_no_finding(self):
        n = make_valid_nhs_number("990000001")
        patient = _patient(identifier=[{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": n}])
        assert RULES["IDENT-003"].evaluate(_ctx(patient)) == []

    def test_missing_nhs_number_fires(self):
        assert RULES["IDENT-001"].evaluate(_ctx(_patient(identifier=[])))


class TestTemporal:
    def test_encounter_end_before_start(self):
        enc = {
            "resourceType": "Encounter", "id": "e1", "status": "finished",
            "period": {"start": "2026-09-01T09:02:00Z", "end": "2026-08-30T10:00:00Z"},
        }
        assert RULES["TEMP-003"].evaluate(_ctx(enc))

    def test_encounter_valid_period(self):
        enc = {
            "resourceType": "Encounter", "id": "e1", "status": "finished",
            "period": {"start": "2026-09-01T09:02:00Z", "end": "2026-09-03T10:00:00Z"},
        }
        assert RULES["TEMP-003"].evaluate(_ctx(enc)) == []

    def test_future_birth_date(self):
        assert RULES["TEMP-001"].evaluate(_ctx(_patient(birthDate="2031-04-02")))


class TestPhysiological:
    def test_decimal_shift_fires(self):
        assert RULES["PHYS-001"].evaluate(_ctx(_observation(value=1420.0)))

    def test_normal_value_no_finding(self):
        assert RULES["PHYS-001"].evaluate(_ctx(_observation(value=120.0))) == []

    def test_spo2_sentinel(self):
        obs = _observation(code="431314004", value=0.0)
        assert RULES["PHYS-004"].evaluate(_ctx(obs))


class TestReferential:
    def test_dangling_subject(self):
        obs = _observation()
        assert RULES["REF-001"].evaluate(_ctx(obs, reference_exists=lambda r: False))

    def test_resolved_subject(self):
        obs = _observation()
        assert RULES["REF-001"].evaluate(_ctx(obs, reference_exists=lambda r: True)) == []


class TestTerminology:
    def test_icd10_valid(self):
        cond = {"resourceType": "Condition", "id": "c1",
                "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "E11.9"}]}}
        assert RULES["TERM-006"].evaluate(_ctx(cond)) == []

    def test_icd10_invalid(self):
        cond = {"resourceType": "Condition", "id": "c1",
                "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "BAD!"}]}}
        assert RULES["TERM-006"].evaluate(_ctx(cond))


class TestRequired:
    def test_observation_no_status(self):
        obs = _observation()
        obs.pop("status")
        assert RULES["REQ-005"].evaluate(_ctx(obs))

    def test_observation_no_code(self):
        obs = _observation()
        obs["code"] = {"coding": []}
        assert RULES["REQ-006"].evaluate(_ctx(obs))


class TestStructural:
    def test_missing_profile(self):
        patient = _patient()
        patient.setdefault("meta", {})["profile"] = []
        assert RULES["PROF-002"].evaluate(_ctx(patient))

    def test_mojibake(self):
        patient = _patient(name=[{"family": "Sm\u00c3\u00a9th", "given": ["A"]}])
        assert RULES["STRUCT-004"].evaluate(_ctx(patient))

    def test_unknown_extension(self):
        patient = _patient()
        patient["extension"] = [{"url": "http://example.org/unknown-extension"}]
        assert RULES["STRUCT-002"].evaluate(_ctx(patient))


class TestExpandedPhysiological:
    @pytest.mark.parametrize("rule_id,code,good,bad", [
        ("PHYS-009", "60621009", 25.0, 999.0),
        ("PHYS-010", "434912009", 6.0, 999.0),
        ("PHYS-011", "59573005", 4.0, 99.0),
        ("PHYS-012", "70901006", 80.0, 9999.0),
        ("PHYS-013", "165581004", 1.0, 999.0),
    ])
    def test_range_positive_and_negative(self, rule_id, code, good, bad):
        assert RULES[rule_id].evaluate(_ctx(_observation(code=code, value=bad)))
        assert RULES[rule_id].evaluate(_ctx(_observation(code=code, value=good))) == []


class TestExpandedRules:
    def test_identifier_format(self):
        patient = _patient(identifier=[{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "ABC"}])
        assert RULES["IDENT-009"].evaluate(_ctx(patient))

    def test_observation_in_future(self):
        obs = _observation()
        obs["effectiveDateTime"] = "2031-01-01T00:00:00Z"
        assert RULES["TEMP-008"].evaluate(_ctx(obs))

    def test_encounter_status_absent(self):
        enc = {"resourceType": "Encounter", "id": "e1"}
        assert RULES["REQ-008"].evaluate(_ctx(enc))

    def test_medication_subject_dangling(self):
        med = {"resourceType": "MedicationRequest", "id": "m1", "status": "active",
               "medicationCodeableConcept": {"coding": [{"system": "https://dmd.nhs.uk/", "code": "317935006"}]},
               "subject": {"reference": "Patient/missing"}}
        assert RULES["REF-006"].evaluate(_ctx(med, reference_exists=lambda r: False))

    def test_observations_without_encounters(self):
        patient = _patient()
        ctx = RuleContext(resource=patient, resource_type="Patient",
                          patient_resources=[patient, _observation()])
        assert RULES["COH-004"].evaluate(ctx)


class TestIdentifierCrossPatient:
    def test_shared_nhs_number_fires(self):
        owners = {"9900000001": ["p1", "p2"]}
        patient = _patient(identifier=[{"system": "https://fhir.nhs.uk/Id/nhs-number",
                                        "value": "9900000001"}])
        patient["id"] = "p1"
        ctx = RuleContext(resource=patient, resource_type="Patient", nhs_number_owners=owners)
        findings = RULES["IDENT-005"].evaluate(ctx)
        assert findings
        assert findings[0].context["patient_ids"] == ["p1", "p2"]

    def test_shared_nhs_number_emits_once_on_lowest_id(self):
        owners = {"9900000001": ["p1", "p2"]}
        patient = _patient(identifier=[{"system": "https://fhir.nhs.uk/Id/nhs-number",
                                        "value": "9900000001"}])
        patient["id"] = "p2"  # not the lowest -> no duplicate finding
        ctx = RuleContext(resource=patient, resource_type="Patient", nhs_number_owners=owners)
        assert RULES["IDENT-005"].evaluate(ctx) == []

    def test_unique_nhs_number_no_finding(self):
        owners = {"9900000001": ["p1"], "9900000002": ["p2"]}
        patient = _patient(identifier=[{"system": "https://fhir.nhs.uk/Id/nhs-number",
                                        "value": "9900000001"}])
        patient["id"] = "p1"
        ctx = RuleContext(resource=patient, resource_type="Patient", nhs_number_owners=owners)
        assert RULES["IDENT-005"].evaluate(ctx) == []


class TestStructuralIntegrity:
    def test_missing_id_fires(self):
        obs = _observation()
        obs.pop("id")
        assert RULES["STRUCT-001"].evaluate(_ctx(obs))

    def test_missing_resource_type_fires(self):
        resource = {"id": "o1", "status": "final"}
        assert RULES["STRUCT-001"].evaluate(_ctx(resource))

    def test_wellformed_resource_no_finding(self):
        assert RULES["STRUCT-001"].evaluate(_ctx(_observation())) == []

    def test_unknown_element_fires(self):
        obs = _observation()
        obs["favouriteColour"] = "blue"
        assert RULES["STRUCT-003"].evaluate(_ctx(obs))

    def test_no_unknown_element(self):
        assert RULES["STRUCT-003"].evaluate(_ctx(_observation())) == []
