"""Rebuild all relational projections from the FHIR source of truth.

Projections are disposable; this script proves they can be regenerated from
``fhir_resource.payload`` alone. See docs/DECISIONS.md ADR-003.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.models import (  # noqa: E402
    Condition,
    Encounter,
    FhirResource,
    MedicationRequest,
    Observation,
    Patient,
)
from app.db.session import async_session_factory  # noqa: E402
from app.domain.fhir.projections import build_projection  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402


async def _rebuild() -> None:
    async with async_session_factory() as session:
        for model in (MedicationRequest, Condition, Observation, Encounter, Patient):
            await session.execute(delete(model))

        rows = (await session.execute(select(FhirResource))).scalars().all()

        # Pass 1: Patients.
        patient_id_by_lid: dict[str, object] = {}
        for row in rows:
            if row.resource_type != "Patient":
                continue
            proj = build_projection("Patient", row.payload)
            session.add(Patient(resource_id=row.id, **proj))
            patient_id_by_lid[row.logical_id] = row.id
        await session.flush()

        # Pass 2: everything else.
        for row in rows:
            if row.resource_type == "Patient":
                continue
            proj = build_projection(row.resource_type, row.payload)
            if proj is None:
                continue
            pid = None
            subject = (row.payload.get("subject") or {}).get("reference")
            if subject:
                pid = patient_id_by_lid.get(subject.rsplit("/", 1)[-1])
            if pid is None:
                continue
            model = {
                "Encounter": Encounter,
                "Observation": Observation,
                "Condition": Condition,
                "MedicationRequest": MedicationRequest,
            }.get(row.resource_type)
            if model is None:
                continue
            session.add(model(resource_id=row.id, patient_id=pid, **proj))

        await session.commit()
        print(f"rebuilt projections for {len(rows)} resources")


def main() -> None:
    asyncio.run(_rebuild())


if __name__ == "__main__":
    main()
