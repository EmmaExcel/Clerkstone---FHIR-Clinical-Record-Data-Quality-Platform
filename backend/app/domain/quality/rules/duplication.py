"""Duplication rules (category: duplication).

These compare a resource against its patient's sibling resources (provided via
``ctx.patient_resources``). Each duplicate group is reported once: the rule fires
on the lexicographically *later* logical id only.
"""

from __future__ import annotations

from app.domain.quality.rules.base import (
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)
from app.domain.quality.rules.util import parse_datetime


def _code_key(resource: dict) -> str | None:
    coding = ((resource.get("code") or {}).get("coding") or [{}])[0] or {}
    return coding.get("code")


def _is_later_duplicate(current: dict, other: dict) -> bool:
    cur_id = current.get("id") or ""
    oth_id = other.get("id") or ""
    return bool(oth_id) and cur_id > oth_id


class DuplicateObservation(Rule):
    id = "DUP-001"
    category = "duplication"
    severity = SEVERITY_WARNING
    title = "Duplicate observation"
    description = "Two Observations for the same patient share the same code, effective time and value."
    fhirpath = "Observation.effective[x]"
    suggested_action = "De-duplicate the observation; keep the source-of-truth copy."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        effective = ctx.resource.get("effectiveDateTime")
        value = (ctx.resource.get("valueQuantity") or {}).get("value")
        code = _code_key(ctx.resource)
        for other in ctx.patient_resources:
            if other.get("resourceType") != "Observation":
                continue
            if other.get("id") == ctx.resource.get("id"):
                continue
            if (
                _code_key(other) == code
                and other.get("effectiveDateTime") == effective
                and (other.get("valueQuantity") or {}).get("value") == value
                and _is_later_duplicate(ctx.resource, other)
            ):
                findings.append(
                    self._finding(
                        ctx,
                        f"Duplicate observation: same code {code!r}, effective {effective!r}, value {value!r}.",
                        context={"code": code, "effective": effective, "value": value},
                    )
                )
                break
        return findings


class DuplicateEncounter(Rule):
    id = "DUP-002"
    category = "duplication"
    severity = SEVERITY_WARNING
    title = "Duplicate encounter"
    description = "Two Encounters for the same patient share the same class and a start time within 5 minutes."
    fhirpath = "Encounter.period.start"
    suggested_action = "Merge the duplicate encounters."
    applies_to = frozenset({"Encounter"})

    def evaluate(self, ctx: RuleContext) -> list:
        findings = []
        cls = ((ctx.resource.get("class") or {}).get("coding") or [{}])[0].get("code")
        start = parse_datetime((ctx.resource.get("period") or {}).get("start"))
        if start is None:
            return []
        for other in ctx.patient_resources:
            if other.get("resourceType") != "Encounter":
                continue
            if other.get("id") == ctx.resource.get("id"):
                continue
            other_cls = ((other.get("class") or {}).get("coding") or [{}])[0].get("code")
            other_start = parse_datetime((other.get("period") or {}).get("start"))
            if other_start is None:
                continue
            delta_min = abs((other_start - start).total_seconds()) / 60
            if other_cls == cls and delta_min <= 5 and _is_later_duplicate(ctx.resource, other):
                findings.append(
                    self._finding(
                        ctx,
                        f"Duplicate encounter: same class {cls!r}, start within {delta_min:.1f} min.",
                        context={"class": cls, "delta_min": round(delta_min, 1)},
                    )
                )
                break
        return findings
