"""Low-level FHIR resource helpers: parse, identify, hash.

The raw JSON resource (JSONB in ``fhir_resource``) is the source of truth;
these helpers validate structure, extract identity, and compute the integrity
hash used by the audit chain.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fhir.resources.R4B import get_fhir_model_class

NHS_NUMBER_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"

# Resource types Clerkstone stores and projects. Bundle is handled separately.
SUPPORTED_RESOURCE_TYPES = {
    "Patient",
    "Encounter",
    "Observation",
    "Condition",
    "MedicationRequest",
    "AllergyIntolerance",
    "Procedure",
    "Immunization",
    "DiagnosticReport",
    "Organization",
    "Practitioner",
    "PractitionerRole",
    "Provenance",
}


def resource_type_of(data: dict[str, Any]) -> str:
    return str(data.get("resourceType", "") or "")


def logical_id_of(data: dict[str, Any]) -> str | None:
    raw = data.get("id")
    return str(raw) if raw else None


def canonical_json(data: dict[str, Any]) -> bytes:
    """Deterministic byte encoding used for integrity hashing."""
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def security_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(data)).hexdigest()


def parse_resource(data: dict[str, Any]) -> Any:
    """Validate a single FHIR resource structurally via fhir.resources.

    Raises ``ValueError`` for a missing/unknown resourceType and propagates the
    underlying Pydantic ``ValidationError`` for structural failures.
    """
    rt = resource_type_of(data)
    if not rt:
        raise ValueError("Resource is missing 'resourceType'")
    if rt not in SUPPORTED_RESOURCE_TYPES:
        raise ValueError(f"Unsupported resourceType: {rt!r}")
    model = get_fhir_model_class(rt)
    return model.model_validate(data)
