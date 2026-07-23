from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Condition, Encounter, FhirResource, MedicationRequest, Observation, Patient


async def export_patient_bundle(
    session: AsyncSession, patient_logical_id: str
) -> dict[str, Any]:
    patient = await session.scalar(
        select(Patient).where(Patient.logical_id == patient_logical_id)
    )
    if patient is None:
        return {"resourceType": "Bundle", "type": "searchset", "entry": []}

    resource_ids = {patient.resource_id}
    for model in (Encounter, Observation, Condition, MedicationRequest):
        ids = (await session.execute(
            select(model.resource_id).where(model.patient_id == patient.resource_id)
        )).scalars().all()
        resource_ids.update(ids)

    rows = (await session.execute(
        select(FhirResource).where(FhirResource.id.in_(resource_ids))
    )).scalars().all()

    entries = [
        {"fullUrl": f"urn:uuid:{r.logical_id}", "resource": r.payload} for r in rows
    ]
    return {"resourceType": "Bundle", "type": "searchset", "entry": entries}
