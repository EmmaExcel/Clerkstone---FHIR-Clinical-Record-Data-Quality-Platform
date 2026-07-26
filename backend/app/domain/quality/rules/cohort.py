"""Cohort-level completeness rules (category: cohort).

Evaluated once per Patient using the patient's full resource set (in
``ctx.patient_resources``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.quality.rules.base import (
    SEVERITY_INFO,
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)
from app.domain.quality.rules.util import parse_date, parse_datetime

_SNOMED_DIABETES = "44054006"
_SNOMED_HYPERTENSION = "38341003"
_HBA1C_CODES = {"43396009", "4548-4"}
_BP_CODES = {"271649006", "271650006"}


def _has_condition(resources: list[dict], snomed_code: str) -> bool:
    for r in resources:
        if r.get("resourceType") != "Condition":
            continue
        for coding in (r.get("code") or {}).get("coding") or []:
            if coding.get("code") == snomed_code:
                return True
    return False


def _obs_codes_in_window(
    resources: list[dict], codes: set[str], since: datetime
) -> bool:
    for r in resources:
        if r.get("resourceType") != "Observation":
            continue
        for coding in (r.get("code") or {}).get("coding") or []:
            if coding.get("code") in codes:
                eff = parse_datetime(r.get("effectiveDateTime"))
                if eff and eff >= since:
                    return True
    return False


def _obs_codes(resources: list[dict], codes: set[str]) -> bool:
    for r in resources:
        if r.get("resourceType") != "Observation":
            continue
        for coding in (r.get("code") or {}).get("coding") or []:
            if coding.get("code") in codes:
                return True
    return False


class EncounterWithoutObservations(Rule):
    id = "COH-001"
    category = "cohort"
    severity = SEVERITY_INFO
    title = "Patient has encounters but no observations"
    description = "The patient has at least one Encounter but no Observation records."
    fhirpath = "Patient"
    suggested_action = "Review whether observations failed to migrate or were intentionally absent."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        types = {r.get("resourceType") for r in ctx.patient_resources}
        if "Encounter" in types and "Observation" not in types:
            return [self._finding(ctx, "Patient has encounters but no observations.")]
        return []


class DiabetesWithoutHba1c(Rule):
    id = "COH-002"
    category = "cohort"
    severity = SEVERITY_WARNING
    title = "Diabetic patient without recent HbA1c"
    description = "A patient with a diabetes diagnosis has no HbA1c observation in the last 24 months."
    fhirpath = "Patient"
    suggested_action = "Confirm the diabetes diagnosis and locate the HbA1c result."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        resources = ctx.patient_resources
        if not _has_condition(resources, _SNOMED_DIABETES):
            return []
        since = datetime.now(UTC) - timedelta(days=730)
        if not _obs_codes_in_window(resources, _HBA1C_CODES, since):
            return [self._finding(ctx, "Diabetic patient has no HbA1c in the last 24 months.")]
        return []


class HypertensionWithoutBp(Rule):
    id = "COH-003"
    category = "cohort"
    severity = SEVERITY_WARNING
    title = "Hypertensive patient without blood-pressure observations"
    description = "A patient with a hypertension diagnosis has no blood-pressure observations."
    fhirpath = "Patient"
    suggested_action = "Confirm the hypertension diagnosis and locate blood-pressure readings."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        resources = ctx.patient_resources
        if not _has_condition(resources, _SNOMED_HYPERTENSION):
            return []
        if not _obs_codes(resources, _BP_CODES):
            return [self._finding(ctx, "Hypertensive patient has no blood-pressure observations.")]
        return []


class ObservationsWithoutEncounters(Rule):
    id = "COH-004"
    category = "cohort"
    severity = SEVERITY_INFO
    title = "Patient has observations but no encounters"
    description = "The patient has Observation records but no Encounter records."
    fhirpath = "Patient"
    suggested_action = "Review whether encounters failed to migrate."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        types = {r.get("resourceType") for r in ctx.patient_resources}
        if "Observation" in types and "Encounter" not in types:
            return [self._finding(ctx, "Patient has observations but no encounters.")]
        return []


class ElderlyWithoutMedication(Rule):
    id = "COH-005"
    category = "cohort"
    severity = SEVERITY_INFO
    title = "Patient over 65 without medication"
    description = "A patient aged over 65 has no MedicationRequest records."
    fhirpath = "Patient"
    suggested_action = "Review whether the medication list migrated."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        birth = parse_date(ctx.resource.get("birthDate"))
        if birth is None:
            return []
        age_days = (datetime.now(UTC).date() - birth).days
        if age_days <= 65 * 365.25:
            return []
        types = {r.get("resourceType") for r in ctx.patient_resources}
        if "MedicationRequest" not in types:
            return [self._finding(ctx, "Patient over 65 has no medication requests.")]
        return []
