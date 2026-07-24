"""Structural FHIR validation (UK Core profile validation is via the sidecar).

``validate_payload`` returns a list of OperationOutcome ``issue`` dicts. Profile
validation against UK Core is delegated to the HL7 FHIR validator sidecar; when
it is unreachable, structural validation still runs and the outcome notes that
profile validation was skipped.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.domain.fhir.bundle import iter_entries
from app.domain.fhir.resources import parse_resource, resource_type_of


def _issue(severity: str, code: str, diagnostics: str, expression: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"severity": severity, "code": code, "diagnostics": diagnostics}
    if expression:
        out["expression"] = [expression]
    return out


def validate_payload(data: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if resource_type_of(data) == "Bundle":
        for entry in iter_entries(data):
            issues.extend(_validate_resource(entry.resource))
    else:
        issues.extend(_validate_resource(data))
    return issues


def _validate_resource(resource: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        parse_resource(resource)
        return []
    except ValidationError as exc:  # structural/type errors (ValidationError subclasses ValueError)
        return [_issue("error", "invalid", str(exc))]
    except ValueError as exc:  # missing/unsupported resourceType
        return [_issue("error", "not-supported", str(exc))]
