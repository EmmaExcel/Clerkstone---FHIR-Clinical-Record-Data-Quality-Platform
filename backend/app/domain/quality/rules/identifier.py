from __future__ import annotations

from app.domain.fhir.nhs import is_valid
from app.domain.fhir.resources import NHS_NUMBER_SYSTEM
from app.domain.quality.rules.base import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)
from app.domain.quality.rules.util import get_nhs_numbers

_VERIFICATION_EXT = (
    "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
)

# Recognised UK identifier systems (UK Core / NHS). A MRN from a local system
# would use its own OID/URI; anything outside these is flagged for review.
_RECOGNISED_SYSTEMS = {
    "https://fhir.nhs.uk/Id/nhs-number",
    "https://fhir.nhs.uk/Id/ods-organization-code",
    "https://fhir.nhs.uk/Id/gmc-number",
}


class NhsNumberAbsent(Rule):
    id = "IDENT-001"
    category = "identifier"
    severity = SEVERITY_WARNING
    title = "NHS number absent"
    description = "Patient has no identifier in the NHS Number system."
    fhirpath = "Patient.identifier.where(system='https://fhir.nhs.uk/Id/nhs-number')"
    suggested_action = "Trace the NHS number from the PDS (Personal Demographics Service)."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        if not get_nhs_numbers(ctx.resource):
            return [self._finding(ctx, "Patient has no NHS number identifier.")]
        return []


class NhsNumberCheckDigitUnverified(Rule):
    id = "IDENT-002"
    category = "identifier"
    severity = SEVERITY_INFO
    title = "NHS number check digit not verified"
    description = "NHS number present but its verification status is not asserted."
    fhirpath = "Patient.identifier.extension"
    suggested_action = "Assert the PDS verification status on the identifier."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for ident in ctx.resource.get("identifier") or []:
            ident = ident or {}
            if ident.get("system") != NHS_NUMBER_SYSTEM:
                continue
            exts = ident.get("extension") or []
            if not any((e or {}).get("url") == _VERIFICATION_EXT for e in exts):
                findings.append(
                    self._finding(ctx, "NHS number present but verification status not asserted.")
                )
        return findings


class NhsNumberInvalidCheckDigit(Rule):
    id = "IDENT-003"
    category = "identifier"
    severity = SEVERITY_ERROR
    title = "NHS number fails modulus-11 check digit"
    description = "The NHS number does not satisfy the modulus-11 check-digit algorithm."
    fhirpath = "Patient.identifier.value"
    suggested_action = "Re-trace the number; a failed check digit usually indicates a transcription error."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for number in get_nhs_numbers(ctx.resource):
            if not is_valid(number):
                findings.append(
                    self._finding(
                        ctx,
                        f"NHS number {number!r} fails the modulus-11 check-digit algorithm.",
                        context={"nhs_number": number},
                    )
                )
        return findings


class PatientMultipleNhsNumbers(Rule):
    id = "IDENT-004"
    category = "identifier"
    severity = SEVERITY_ERROR
    title = "Patient carries two different NHS numbers"
    description = "A single Patient resource has more than one distinct NHS number."
    fhirpath = "Patient.identifier"
    suggested_action = "Resolve the identifier merge before migration."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        numbers = set(get_nhs_numbers(ctx.resource))
        if len(numbers) > 1:
            return [
                self._finding(
                    ctx,
                    f"Patient carries {len(numbers)} distinct NHS numbers: {sorted(numbers)}.",
                    context={"nhs_numbers": sorted(numbers)},
                )
            ]
        return []


class NhsNumberSharedAcrossPatients(Rule):
    id = "IDENT-005"
    category = "identifier"
    severity = SEVERITY_ERROR
    title = "NHS number shared by multiple patients"
    description = "The same NHS number appears on more than one Patient resource."
    fhirpath = "Patient.identifier.value"
    suggested_action = (
        "Resolve the duplicate identifier before migration; a shared NHS number is a "
        "critical identity hazard."
    )
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        owners = ctx.nhs_number_owners or {}
        findings = []
        emitted: set[str] = set()
        for number in get_nhs_numbers(ctx.resource):
            ids = sorted(set(owners.get(number) or []))
            if len(ids) <= 1 or number in emitted:
                continue
            emitted.add(number)
            # Emit once per shared number, on the lowest-id patient, to avoid a
            # finding on every patient that carries the duplicate.
            if ctx.resource.get("id") == ids[0]:
                findings.append(
                    self._finding(
                        ctx,
                        f"NHS number {number!r} is shared by {len(ids)} patients: {ids}.",
                        context={"nhs_number": number, "patient_ids": ids},
                    )
                )
        return findings


class IdentifierSystemUnrecognised(Rule):
    id = "IDENT-006"
    category = "identifier"
    severity = SEVERITY_WARNING
    title = "Identifier system not recognised"
    description = "An identifier uses a system URI that is not a recognised UK system."
    fhirpath = "Patient.identifier.system"
    suggested_action = "Map the local identifier system to a recognised UK Core system."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for ident in ctx.resource.get("identifier") or []:
            system = (ident or {}).get("system")
            if system and system not in _RECOGNISED_SYSTEMS:
                findings.append(
                    self._finding(
                        ctx,
                        f"Identifier system {system!r} is not a recognised UK system.",
                        context={"system": system},
                    )
                )
        return findings


class MrnPatternMismatch(Rule):
    id = "IDENT-007"
    category = "identifier"
    severity = SEVERITY_WARNING
    title = "MRN pattern mismatch"
    description = "A local MRN identifier does not match the expected pattern."
    fhirpath = "Patient.identifier.value"
    suggested_action = "Confirm the local MRN format with the source system."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for ident in ctx.resource.get("identifier") or []:
            ident = ident or {}
            value = ident.get("value")
            if ident.get("type", {}).get("text") == "MRN" and value and not value.isalnum():
                findings.append(
                    self._finding(ctx, f"MRN {value!r} has unexpected characters.")
                )
        return findings


class NhsNumberFormatInvalid(Rule):
    id = "IDENT-009"
    category = "identifier"
    severity = SEVERITY_ERROR
    title = "NHS number format invalid"
    description = "An NHS number does not match the 10-digit format."
    fhirpath = "Patient.identifier.value"
    suggested_action = "Correct the identifier; NHS numbers are exactly 10 digits."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for number in get_nhs_numbers(ctx.resource):
            if len(number) != 10 or not number.isdigit():
                findings.append(
                    self._finding(
                        ctx,
                        f"NHS number {number!r} is not 10 digits.",
                        context={"nhs_number": number},
                    )
                )
        return findings

