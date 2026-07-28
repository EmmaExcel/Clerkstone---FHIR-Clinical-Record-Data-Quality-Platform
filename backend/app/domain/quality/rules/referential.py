from __future__ import annotations

from app.domain.quality.rules.base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)


def _ref(reference: str | None) -> str | None:
    if not reference:
        return None
    # Normalise "Patient/abc" and "urn:uuid:abc" to "Patient/abc".
    if reference.startswith("urn:uuid:"):
        return None  # can't resolve urn without a resource-type mapping
    return reference


class ObservationSubjectDangling(Rule):
    id = "REF-001"
    category = "referential"
    severity = SEVERITY_ERROR
    title = "Observation subject does not resolve"
    description = "Observation.subject references a Patient that is not in the store."
    fhirpath = "Observation.subject.reference"
    suggested_action = "Repair the dangling reference or ingest the referenced Patient first."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        ref = _ref((ctx.resource.get("subject") or {}).get("reference"))
        if ref and not ctx.reference_exists(ref):
            return [self._finding(ctx, f"Observation.subject {ref!r} does not resolve.")]
        return []


class ObservationSubjectMissing(Rule):
    id = "REF-005"
    category = "referential"
    severity = SEVERITY_WARNING
    title = "Observation has no subject"
    description = "Observation has no subject reference."
    fhirpath = "Observation.subject"
    suggested_action = "Link the observation to its patient."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        if not (ctx.resource.get("subject") or {}).get("reference"):
            return [self._finding(ctx, "Observation.subject is absent.")]
        return []


class EncounterSubjectDangling(Rule):
    id = "REF-002"
    category = "referential"
    severity = SEVERITY_ERROR
    title = "Encounter subject does not resolve"
    description = "Encounter.subject references a Patient that is not in the store."
    fhirpath = "Encounter.subject.reference"
    suggested_action = "Repair the dangling reference."
    applies_to = frozenset({"Encounter"})

    def evaluate(self, ctx: RuleContext) -> list:
        ref = _ref((ctx.resource.get("subject") or {}).get("reference"))
        if ref and not ctx.reference_exists(ref):
            return [self._finding(ctx, f"Encounter.subject {ref!r} does not resolve.")]
        return []


class ConditionEncounterDangling(Rule):
    id = "REF-003"
    category = "referential"
    severity = SEVERITY_ERROR
    title = "Condition encounter does not resolve"
    description = "Condition.encounter references an Encounter that is not in the store."
    fhirpath = "Condition.encounter.reference"
    suggested_action = "Repair the dangling reference."
    applies_to = frozenset({"Condition"})

    def evaluate(self, ctx: RuleContext) -> list:
        ref = _ref((ctx.resource.get("encounter") or {}).get("reference"))
        if ref and not ctx.reference_exists(ref):
            return [self._finding(ctx, f"Condition.encounter {ref!r} does not resolve.")]
        return []


class ObservationEncounterDangling(Rule):
    id = "REF-004"
    category = "referential"
    severity = SEVERITY_ERROR
    title = "Observation encounter does not resolve"
    description = "Observation.encounter references an Encounter that is not in the store."
    fhirpath = "Observation.encounter.reference"
    suggested_action = "Repair the dangling reference."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        ref = _ref((ctx.resource.get("encounter") or {}).get("reference"))
        if ref and not ctx.reference_exists(ref):
            return [self._finding(ctx, f"Observation.encounter {ref!r} does not resolve.")]
        return []


class MedicationSubjectDangling(Rule):
    id = "REF-006"
    category = "referential"
    severity = SEVERITY_ERROR
    title = "MedicationRequest subject does not resolve"
    description = "MedicationRequest.subject references a Patient that is not in the store."
    fhirpath = "MedicationRequest.subject.reference"
    suggested_action = "Repair the dangling reference."
    applies_to = frozenset({"MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        ref = _ref((ctx.resource.get("subject") or {}).get("reference"))
        if ref and not ctx.reference_exists(ref):
            return [self._finding(ctx, f"MedicationRequest.subject {ref!r} does not resolve.")]
        return []
