"""FHIR Bundle ingestion: validate, de-duplicate, store, and project.

Two passes: (1) store every resource as the JSONB source of truth; (2) build the
relational projections once all resources (and thus FKs) are known. Ingestion is
idempotent on ``(resource_type, logical_id, version_id)``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Condition,
    Encounter,
    FhirResource,
    IngestionBundle,
    MedicationRequest,
    Observation,
    Patient,
)
from app.domain.fhir.bundle import (
    bundle_type_of,
    iter_entries,
    parse_bundle,
    resolve_logical_id,
)
from app.domain.fhir.projections import build_projection
from app.domain.fhir.resources import parse_resource, resource_type_of, security_hash

_PROJECTION_MODELS = {
    "Patient": Patient,
    "Encounter": Encounter,
    "Observation": Observation,
    "Condition": Condition,
    "MedicationRequest": MedicationRequest,
}


def _ref_id(reference: str | None) -> str | None:
    if not reference:
        return None
    if reference.startswith("urn:uuid:"):
        return reference[len("urn:uuid:") :]
    if "/" in reference:
        return reference.rsplit("/", 1)[1]
    return reference


@dataclass
class IngestResult:
    bundle_id: uuid.UUID
    status: str  # accepted | partial | rejected
    accepted: int
    rejected: int
    errors: list[dict] = field(default_factory=list)
    resource_ids: dict[str, uuid.UUID] = field(default_factory=dict)


async def ingest_bundle(
    session: AsyncSession, bundle_data: dict, uploaded_by: str
) -> IngestResult:
    parse_bundle(bundle_data)  # structural validation of the Bundle itself
    entries = iter_entries(bundle_data)

    bundle_row = IngestionBundle(
        uploaded_by=uploaded_by,
        bundle_type=bundle_type_of(bundle_data),
        resource_count=len(entries),
        status="accepted",
    )
    session.add(bundle_row)
    await session.flush()

    accepted = 0
    rejected = 0
    errors: list[dict] = []
    resource_rows: dict[str, FhirResource] = {}

    # Pass 1: store resources (source of truth).
    for entry in entries:
        resource = entry.resource
        rt = resource_type_of(resource)
        lid = resolve_logical_id(entry.full_url, resource)
        key = f"{rt}/{lid}"

        if lid is None:
            rejected += 1
            errors.append({"key": key, "error": "missing logical id"})
            continue
        try:
            parse_resource(resource)
        except Exception as exc:  # noqa: BLE001 — capture any structural failure
            rejected += 1
            errors.append({"key": key, "error": str(exc)})
            continue

        existing = await session.scalar(
            select(FhirResource.id).where(
                FhirResource.resource_type == rt,
                FhirResource.logical_id == lid,
                FhirResource.version_id == "1",
            )
        )
        if existing is not None:
            continue  # idempotent — already stored

        row = FhirResource(
            resource_type=rt,
            logical_id=lid,
            version_id="1",
            last_updated=datetime.now(UTC),
            payload=resource,
            source_bundle=bundle_row.id,
            security_hash=security_hash(resource),
        )
        session.add(row)
        resource_rows[key] = row
        accepted += 1

    await session.flush()  # assign resource row ids

    # Pass 2: projections (Patients first, so FKs resolve).
    patient_id_by_lid: dict[str, uuid.UUID] = {}
    for key, row in resource_rows.items():
        if not key.startswith("Patient/"):
            continue
        proj = build_projection("Patient", row.payload)
        if proj is None:
            continue
        session.add(Patient(resource_id=row.id, **proj))
        patient_id_by_lid[row.logical_id] = row.id
    await session.flush()

    for key, row in resource_rows.items():
        rt = key.split("/", 1)[0]
        if rt == "Patient":
            continue
        model = _PROJECTION_MODELS.get(rt)
        if model is None:
            continue
        proj = build_projection(rt, row.payload)
        if proj is None:
            continue

        patient_rid = None
        subject = (row.payload.get("subject") or {}).get("reference")
        if subject:
            pid = _ref_id(subject)
            patient_rid = patient_id_by_lid.get(pid) if pid else None
            if patient_rid is None and pid:
                patient_rid = await session.scalar(
                    select(Patient.resource_id).where(Patient.logical_id == pid)
                )

        if patient_rid is None:
            # Dangling/missing subject: the resource is still stored (source of
            # truth); the projection is skipped and REF-* rules flag the defect.
            continue

        if rt == "Observation":
            encounter_rid = None
            enc_ref = (row.payload.get("encounter") or {}).get("reference")
            if enc_ref:
                enc_lid = _ref_id(enc_ref)
                enc_row = resource_rows.get(f"Encounter/{enc_lid}")
                encounter_rid = enc_row.id if enc_row is not None else None
            session.add(
                Observation(
                    resource_id=row.id, patient_id=patient_rid, encounter_id=encounter_rid, **proj
                )
            )
        else:
            session.add(model(resource_id=row.id, patient_id=patient_rid, **proj))

    await session.flush()

    if rejected and accepted == 0:
        bundle_row.status = "rejected"
    elif rejected:
        bundle_row.status = "partial"
    else:
        bundle_row.status = "accepted"  # includes the idempotent all-already-present case
    bundle_row.resource_count = accepted

    return IngestResult(
        bundle_id=bundle_row.id,
        status=bundle_row.status,
        accepted=accepted,
        rejected=rejected,
        errors=errors,
        resource_ids={k: v.id for k, v in resource_rows.items()},
    )
