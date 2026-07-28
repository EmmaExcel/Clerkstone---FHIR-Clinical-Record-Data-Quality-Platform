from __future__ import annotations

from app.domain.quality.rules.base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)

_VALID_GENDERS = {"male", "female", "other", "unknown"}


class BirthDateAbsent(Rule):
    id = "REQ-001"
    category = "required"
    severity = SEVERITY_WARNING
    title = "Patient birth date absent"
    description = "Patient.birthDate is missing. Birth date is required for age-sensitive cohort and temporal rules."
    fhirpath = "Patient.birthDate"
    suggested_action = "Obtain birth date from the source system or a demography service."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.resource.get("birthDate") is None:
            return [self._finding(ctx, "Patient.birthDate is absent.")]
        return []


class GenderAbsent(Rule):
    id = "REQ-002"
    category = "required"
    severity = SEVERITY_WARNING
    title = "Patient gender absent"
    description = "Patient.gender is missing."
    fhirpath = "Patient.gender"
    suggested_action = "Populate gender from the source system."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.resource.get("gender") is None:
            return [self._finding(ctx, "Patient.gender is absent.")]
        return []


class GenderOutOfValueSet(Rule):
    id = "REQ-003"
    category = "required"
    severity = SEVERITY_WARNING
    title = "Patient gender not in bound value set"
    description = "Patient.gender is not one of the FHIR administrative-gender values."
    fhirpath = "Patient.gender"
    suggested_action = "Map the local value onto the FHIR administrative-gender value set."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        gender = ctx.resource.get("gender")
        if gender is not None and gender not in _VALID_GENDERS:
            return [self._finding(ctx, f"Patient.gender={gender!r} is not in the value set.")]
        return []


class EncounterClassAbsent(Rule):
    id = "REQ-004"
    category = "required"
    severity = SEVERITY_WARNING
    title = "Encounter class absent"
    description = "Encounter.class is missing."
    fhirpath = "Encounter.class"
    suggested_action = "Derive class (inpatient/outpatient/emergency) from the admission record."
    applies_to = frozenset({"Encounter"})

    def evaluate(self, ctx: RuleContext) -> list:
        cls = ctx.resource.get("class")
        if not cls or not (cls.get("coding") or cls.get("code")):
            return [self._finding(ctx, "Encounter.class is absent.")]
        return []


class ObservationStatusAbsent(Rule):
    id = "REQ-005"
    category = "required"
    severity = SEVERITY_ERROR
    title = "Observation status absent"
    description = "Observation.status is required and must be one of the FHIR observation-status values."
    fhirpath = "Observation.status"
    suggested_action = "Populate Observation.status (e.g. final, preliminary, corrected)."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.resource.get("status") is None:
            return [self._finding(ctx, "Observation.status is absent.")]
        return []


class ObservationWithoutCode(Rule):
    id = "REQ-006"
    category = "required"
    severity = SEVERITY_ERROR
    title = "Observation without a code"
    description = "Observation.code is required."
    fhirpath = "Observation.code"
    suggested_action = "Populate Observation.code with a SNOMED CT or LOINC concept."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        code = ctx.resource.get("code")
        if not code or not code.get("coding"):
            return [self._finding(ctx, "Observation has no code.")]
        return []


class PatientNameAbsent(Rule):
    id = "REQ-007"
    category = "required"
    severity = SEVERITY_WARNING
    title = "Patient name absent"
    description = "Patient.name is missing."
    fhirpath = "Patient.name"
    suggested_action = "Populate Patient.name from the source system."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        if not ctx.resource.get("name"):
            return [self._finding(ctx, "Patient.name is absent.")]
        return []


class EncounterStatusAbsent(Rule):
    id = "REQ-008"
    category = "required"
    severity = SEVERITY_ERROR
    title = "Encounter status absent"
    description = "Encounter.status is missing."
    fhirpath = "Encounter.status"
    suggested_action = "Populate Encounter.status."
    applies_to = frozenset({"Encounter"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.resource.get("status") is None:
            return [self._finding(ctx, "Encounter.status is absent.")]
        return []


class MedicationWithoutCode(Rule):
    id = "REQ-009"
    category = "required"
    severity = SEVERITY_ERROR
    title = "MedicationRequest without a medication code"
    description = "MedicationRequest has no medicationCodeableConcept coding."
    fhirpath = "MedicationRequest.medicationCodeableConcept"
    suggested_action = "Populate the medication code (dm+d)."
    applies_to = frozenset({"MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        med = ctx.resource.get("medicationCodeableConcept")
        if not med or not med.get("coding"):
            return [self._finding(ctx, "MedicationRequest has no medication code.")]
        return []
