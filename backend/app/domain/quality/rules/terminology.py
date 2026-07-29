"""Terminology-resolvability rules (category: terminology).

TERM-002/003/004/005 require a terminology resolver (the DI seam). When no
resolver is configured they are skipped rather than firing spuriously; the
format checks (TERM-001, TERM-006) run without a resolver.
"""

from __future__ import annotations

import re

from app.domain.quality.rules.base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)

SNOMED_SYSTEM = "http://snomed.info/sct"
LOINC_SYSTEM = "http://loinc.org"
DMD_SYSTEM = "https://dmd.nhs.uk/"
ICD10_SYSTEM = "http://hl7.org/fhir/sid/icd-10"

_RECOGNISED_SYSTEMS = {SNOMED_SYSTEM, LOINC_SYSTEM, DMD_SYSTEM, ICD10_SYSTEM}

ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9AB](\.[0-9A-TV-Z]{1,4})?$")


class CodeSystemUnrecognised(Rule):
    id = "TERM-001"
    category = "terminology"
    severity = SEVERITY_WARNING
    title = "Code system not recognised"
    description = "A coding uses a system URI that is not a recognised terminology system."
    fhirpath = "*.code.coding.system"
    suggested_action = "Map the local code system to a recognised terminology."
    applies_to = frozenset({"Observation", "Condition", "MedicationRequest", "Procedure"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for coding in (ctx.resource.get("code") or {}).get("coding") or []:
            system = coding.get("system")
            if system and system not in _RECOGNISED_SYSTEMS:
                findings.append(
                    self._finding(
                        ctx,
                        f"Code system {system!r} is not recognised.",
                        context={"system": system, "code": coding.get("code")},
                    )
                )
        return findings


class SnomedCodeUnresolvable(Rule):
    id = "TERM-002"
    category = "terminology"
    severity = SEVERITY_WARNING
    title = "SNOMED CT code not resolvable"
    description = "A SNOMED CT code cannot be resolved by the terminology service."
    fhirpath = "*.code.coding.where(system='http://snomed.info/sct')"
    suggested_action = "Confirm the code against the SNOMED CT UK Edition."
    applies_to = frozenset({"Observation", "Condition", "Procedure"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.terminology is None:
            return []
        findings = []
        for coding in (ctx.resource.get("code") or {}).get("coding") or []:
            if coding.get("system") != SNOMED_SYSTEM:
                continue
            code = coding.get("code")
            if code and ctx.terminology.resolve(SNOMED_SYSTEM, code) is None:
                findings.append(
                    self._finding(ctx, f"SNOMED CT code {code!r} is not resolvable.",
                                  context={"code": code})
                )
        return findings


class DmdCodeUnresolvable(Rule):
    id = "TERM-003"
    category = "terminology"
    severity = SEVERITY_WARNING
    title = "dm+d code not resolvable"
    description = "A dm+d code cannot be resolved by the terminology service."
    fhirpath = "MedicationRequest.medicationCodeableConcept.coding"
    suggested_action = "Confirm the code against dm+d."
    applies_to = frozenset({"MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.terminology is None:
            return []
        findings = []
        for coding in (ctx.resource.get("medicationCodeableConcept") or {}).get("coding") or []:
            if coding.get("system") != DMD_SYSTEM:
                continue
            code = coding.get("code")
            if code and ctx.terminology.resolve(DMD_SYSTEM, code) is None:
                findings.append(
                    self._finding(ctx, f"dm+d code {code!r} is not resolvable.",
                                  context={"code": code})
                )
        return findings


class DisplayMismatch(Rule):
    id = "TERM-004"
    category = "terminology"
    severity = SEVERITY_WARNING
    title = "Display text disagrees with resolved term"
    description = "A coding's display text does not match the terminology's preferred term."
    fhirpath = "*.code.coding.display"
    suggested_action = "Refresh the display text from the terminology service."
    applies_to = frozenset({"Observation", "Condition", "MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.terminology is None:
            return []
        findings = []
        for coding in (ctx.resource.get("code") or {}).get("coding") or []:
            system, code, display = coding.get("system"), coding.get("code"), coding.get("display")
            if not (system and code and display):
                continue
            resolved = ctx.terminology.resolve(system, code)
            if resolved and resolved.get("display") and resolved["display"] != display:
                findings.append(
                    self._finding(
                        ctx,
                        f"Display {display!r} disagrees with resolved term {resolved['display']!r}.",
                        context={"code": code, "display": display, "resolved": resolved["display"]},
                    )
                )
        return findings


class RetiredCodeUsed(Rule):
    id = "TERM-005"
    category = "terminology"
    severity = SEVERITY_WARNING
    title = "Retired code in use"
    description = "A coding uses a concept that is retired/inactive in the terminology."
    fhirpath = "*.code.coding"
    suggested_action = "Replace the retired concept with its active replacement."
    applies_to = frozenset({"Observation", "Condition", "MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.terminology is None:
            return []
        findings = []
        for coding in (ctx.resource.get("code") or {}).get("coding") or []:
            system, code = coding.get("system"), coding.get("code")
            if not (system and code):
                continue
            resolved = ctx.terminology.resolve(system, code)
            if resolved and resolved.get("active") is False:
                findings.append(
                    self._finding(ctx, f"Code {code!r} is retired/inactive.",
                                  context={"code": code})
                )
        return findings


class Icd10FormatInvalid(Rule):
    id = "TERM-006"
    category = "terminology"
    severity = SEVERITY_ERROR
    title = "ICD-10 code format invalid"
    description = "An ICD-10 code does not match the expected format."
    fhirpath = "*.code.coding.where(system='http://hl7.org/fhir/sid/icd-10')"
    suggested_action = "Correct the ICD-10 code."
    applies_to = frozenset({"Condition"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for coding in (ctx.resource.get("code") or {}).get("coding") or []:
            if coding.get("system") != ICD10_SYSTEM:
                continue
            code = coding.get("code") or ""
            if not ICD10_PATTERN.match(code):
                findings.append(
                    self._finding(ctx, f"ICD-10 code {code!r} has an invalid format.",
                                  context={"code": code})
                )
        return findings


class LoincCodeUnresolvable(Rule):
    id = "TERM-007"
    category = "terminology"
    severity = SEVERITY_WARNING
    title = "LOINC code not resolvable"
    description = "A LOINC code cannot be resolved by the terminology service."
    fhirpath = "*.code.coding.where(system='http://loinc.org')"
    suggested_action = "Confirm the code against LOINC."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        if ctx.terminology is None:
            return []
        findings = []
        for coding in (ctx.resource.get("code") or {}).get("coding") or []:
            if coding.get("system") != LOINC_SYSTEM:
                continue
            code = coding.get("code")
            if code and ctx.terminology.resolve(LOINC_SYSTEM, code) is None:
                findings.append(
                    self._finding(ctx, f"LOINC code {code!r} is not resolvable.",
                                  context={"code": code})
                )
        return findings


class DmdCodeFormatInvalid(Rule):
    id = "TERM-008"
    category = "terminology"
    severity = SEVERITY_WARNING
    title = "dm+d code format invalid"
    description = "A dm+d code does not match the expected 9-digit numeric format."
    fhirpath = "MedicationRequest.medicationCodeableConcept.coding"
    suggested_action = "Correct the dm+d code."
    applies_to = frozenset({"MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for coding in (ctx.resource.get("medicationCodeableConcept") or {}).get("coding") or []:
            if coding.get("system") != DMD_SYSTEM:
                continue
            code = coding.get("code") or ""
            if len(code) != 9 or not code.isdigit():
                findings.append(
                    self._finding(ctx, f"dm+d code {code!r} is not 9 digits.",
                                  context={"code": code})
                )
        return findings
