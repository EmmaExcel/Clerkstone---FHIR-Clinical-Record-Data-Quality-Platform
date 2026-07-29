from __future__ import annotations

import unicodedata

from fhir.resources.R4B import get_fhir_model_class

from app.domain.quality.rules.base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)

# Mojibake / replacement / combining-character signals. NHS England documented
# incorrectly-decoded special characters as a known issue in its own synthetic
# notes dataset.
_MOJIBAKE_MARKERS = ("\ufffd", "Ã", "â€", "Â", "Ã©", "Ã¨")
_COMBINING_RANGE = ("\u0300", "\u036f")


class MalformedResource(Rule):
    id = "STRUCT-001"
    category = "structural"
    severity = SEVERITY_ERROR
    title = "Malformed or truncated resource"
    description = "The resource is missing its logical id or its resourceType."
    fhirpath = "Resource.id | Resource.resourceType"
    suggested_action = "Re-export the source record; a truncated payload usually indicates a failed extraction."
    applies_to = frozenset(
        {
            "Patient", "Encounter", "Observation", "Condition", "MedicationRequest",
            "AllergyIntolerance", "Procedure", "Immunization", "DiagnosticReport",
            "Organization", "Practitioner", "PractitionerRole", "Provenance",
        }
    )

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        if not isinstance(ctx.resource, dict) or not ctx.resource:
            return [self._finding(ctx, "Resource payload is empty or not a JSON object.")]
        if not ctx.resource_type:
            findings.append(self._finding(ctx, "Resource is missing 'resourceType'."))
        if not ctx.resource.get("id"):
            findings.append(self._finding(ctx, "Resource is missing its logical 'id'."))
        return findings


class ProfileAbsent(Rule):
    id = "PROF-002"
    category = "structural"
    severity = SEVERITY_WARNING
    title = "UK Core profile not asserted"
    description = "meta.profile is absent where the UK Core profile is mandated."
    fhirpath = "Resource.meta.profile"
    suggested_action = "Assert the relevant UK Core profile in meta.profile."
    applies_to = frozenset({"Patient", "Encounter", "Observation", "Condition", "MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        profiles = (ctx.resource.get("meta") or {}).get("profile") or []
        if not profiles:
            return [self._finding(ctx, f"{ctx.resource_type}.meta.profile is absent.")]
        return []


class MojibakeDetected(Rule):
    id = "STRUCT-004"
    category = "structural"
    severity = SEVERITY_WARNING
    title = "Encoding corruption (mojibake) detected"
    description = "A text field contains mojibake or combining-character anomalies."
    fhirpath = "Patient.name.family | Patient.name.given"
    suggested_action = "Re-decode the source text as UTF-8; correct the special characters."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for name in ctx.resource.get("name") or []:
            for key in ("family", "given"):
                value = name.get(key)
                text = " ".join(value) if isinstance(value, list) else value
                if not text:
                    continue
                if any(m in text for m in _MOJIBAKE_MARKERS):
                    findings.append(
                        self._finding(ctx, f"Name field {key!r} contains mojibake: {text!r}.",
                                      context={"field": key})
                    )
                elif any(_COMBINING_RANGE[0] <= ch <= _COMBINING_RANGE[1] for ch in text):
                    if any(unicodedata.combining(ch) for ch in text):
                        findings.append(
                            self._finding(ctx, f"Name field {key!r} has combining-character anomalies.",
                                          context={"field": key})
                        )
        return findings


_KNOWN_EXTENSIONS = {
    "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus",
    "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-EthnicCategory",
}


class UnknownElement(Rule):
    id = "STRUCT-003"
    category = "structural"
    severity = SEVERITY_WARNING
    title = "Unknown element present"
    description = "The resource carries a top-level element not defined for its resourceType in FHIR R4."
    fhirpath = "Resource"
    suggested_action = "Map the unknown element to a FHIR extension or remove it."
    applies_to = frozenset(
        {
            "Patient", "Encounter", "Observation", "Condition", "MedicationRequest",
            "AllergyIntolerance", "Procedure", "Immunization", "DiagnosticReport",
            "Organization", "Practitioner", "PractitionerRole", "Provenance",
        }
    )

    def evaluate(self, ctx: RuleContext) -> list:
        if not ctx.resource_type:
            return []
        try:
            model = get_fhir_model_class(ctx.resource_type)
        except Exception:  # noqa: BLE001 — unknown type has no model; nothing to diff
            return []
        known = {"resourceType"}
        for name, info in model.model_fields.items():
            known.add(name)
            if info.alias:
                known.add(info.alias)
        unknown = sorted(set(ctx.resource.keys()) - known)
        if not unknown:
            return []
        return [
            self._finding(ctx, f"Unknown element(s): {', '.join(unknown)}.", context={"elements": unknown})
        ]


class UnknownExtensionUrl(Rule):
    id = "STRUCT-002"
    category = "structural"
    severity = SEVERITY_WARNING
    title = "Unknown extension URL"
    description = "A resource carries an extension whose URL is not a registered UK Core extension."
    fhirpath = "*.extension.url"
    suggested_action = "Register the extension or map it to a UK Core extension."
    applies_to = frozenset({"Patient", "Encounter", "Observation", "Condition", "MedicationRequest"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        for ext in ctx.resource.get("extension") or []:
            url = (ext or {}).get("url")
            if url and url not in _KNOWN_EXTENSIONS:
                findings.append(
                    self._finding(ctx, f"Unknown extension URL {url!r}.", context={"url": url})
                )
        return findings
