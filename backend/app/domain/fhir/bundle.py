"""FHIR Bundle handling: transaction/collection semantics and idempotency.

A Bundle of type ``transaction`` or ``collection`` is the ingestion unit. Each
entry carries a ``fullUrl`` (an ``urn:uuid:`` or absolute URL) and an optional
``request`` (``method``/``url``). Clerkstone de-duplicates by
``(resourceType, logical_id, version_id)`` so a retried bundle cannot double-create.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fhir.resources.R4B.bundle import Bundle as BundleModel

from app.domain.fhir.resources import logical_id_of, resource_type_of


@dataclass(frozen=True)
class EntryResource:
    full_url: str | None
    resource: dict[str, Any]
    method: str | None
    url: str | None


def parse_bundle(data: dict[str, Any]) -> BundleModel:
    if resource_type_of(data) != "Bundle":
        raise ValueError("Ingestion payload must be a FHIR Bundle")
    return BundleModel.model_validate(data)


def bundle_type_of(data: dict[str, Any]) -> str:
    return str(data.get("type") or "collection")


def iter_entries(data: dict[str, Any]) -> list[EntryResource]:
    """Extract entry resources, tolerating entries with no resource (e.g. DELETE)."""
    out: list[EntryResource] = []
    for entry in data.get("entry") or []:
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            continue
        request = entry.get("request") or {}
        out.append(
            EntryResource(
                full_url=entry.get("fullUrl"),
                resource=resource,
                method=request.get("method"),
                url=request.get("url"),
            )
        )
    return out


def resolve_logical_id(full_url: str | None, resource: dict[str, Any]) -> str | None:
    """Return the logical id, deriving one from an ``urn:uuid:`` fullUrl if absent."""
    lid = logical_id_of(resource)
    if lid:
        return lid
    if full_url and full_url.startswith("urn:uuid:"):
        return full_url[len("urn:uuid:") :]
    return None
