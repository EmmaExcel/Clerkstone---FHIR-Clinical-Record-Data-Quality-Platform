from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.errors import FhirError
from app.config import get_settings
from app.core.auth import CurrentUser, require_role
from app.db.models import (
    Condition,
    DqFinding,
    Encounter,
    MedicationRequest,
    Observation,
    Patient,
)
from app.dependencies import SessionDep
from app.domain.fhir.export import export_patient_bundle

router = APIRouter(prefix="/patients", tags=["patients"])

Reader = Annotated[CurrentUser, Depends(require_role("reader"))]
Analyst = Annotated[CurrentUser, Depends(require_role("analyst"))]

SYNTHETIC_NOTICE = (
    "All records in this system are synthetically generated. "
    "This is a portfolio prototype and must not be used for patient care."
)


def _age_years(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    today = datetime.now(UTC).date()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def _demographics(p: Patient) -> dict[str, Any]:
    """Full patient demographics, matching the frontend ``PatientDemographics`` shape."""
    return {
        "id": p.logical_id,
        "nhs_number": p.nhs_number,
        "nhs_number_status": p.nhs_number_status,
        "family_name": p.family_name,
        "given_names": p.given_names or [],
        "birth_date": p.birth_date.isoformat() if p.birth_date else None,
        "age_years": _age_years(p.birth_date),
        "gender": p.gender,
        "postcode": p.postcode,
        "deceased": p.deceased,
    }


def _clamp_count(count: int | None) -> int:
    settings = get_settings()
    if count is None or count < 1:
        return 20
    return min(count, settings.max_page_size)


async def _get_patient(session: SessionDep, logical_id: str) -> Patient:
    patient = await session.scalar(select(Patient).where(Patient.logical_id == logical_id))
    if patient is None:
        raise FhirError(404, "not-found", f"Patient/{logical_id} not found")
    return patient


@router.get("")
async def search_patients(
    session: SessionDep,
    user: Reader,
    family: str | None = None,
    birthdate: str | None = None,
    gender: str | None = None,
    _count: int | None = Query(default=None),
    _page: int | None = Query(default=0),
) -> dict[str, Any]:
    count = _clamp_count(_count)
    page = max(0, _page or 0)

    stmt = select(Patient)
    if family:
        stmt = stmt.where(Patient.family_name.ilike(f"{family}%"))
    if birthdate:
        stmt = stmt.where(Patient.birth_date == birthdate)
    if gender:
        stmt = stmt.where(Patient.gender == gender)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await session.execute(stmt.order_by(Patient.family_name).offset(page * count).limit(count))).scalars().all()

    return {
        "synthetic_data_notice": SYNTHETIC_NOTICE,
        "total": total or 0,
        "patients": [_demographics(p) for p in rows],
        "page": {"count": len(rows), "page": page, "next": (page + 1) if len(rows) == count else None},
    }


@router.get("/{patient_id}")
async def patient_summary(patient_id: str, session: SessionDep, user: Reader) -> dict[str, Any]:
    patient = await _get_patient(session, patient_id)
    counts = {}
    for model, name in (
        (Encounter, "encounters"),
        (Observation, "observations"),
        (Condition, "conditions"),
        (MedicationRequest, "medications"),
    ):
        counts[name] = await session.scalar(
            select(func.count()).where(model.patient_id == patient.resource_id)
        )
    return {
        "patient": _demographics(patient),
        "counts": counts,
        "synthetic_data_notice": SYNTHETIC_NOTICE,
    }


@router.get("/{patient_id}/timeline")
async def patient_timeline(
    patient_id: str,
    session: SessionDep,
    user: Reader,
    _count: int | None = Query(default=None),
) -> dict[str, Any]:
    patient = await _get_patient(session, patient_id)
    count = _clamp_count(_count)

    encounters = (await session.execute(
        select(Encounter).where(Encounter.patient_id == patient.resource_id).order_by(Encounter.period_start.desc())
    )).scalars().all()
    observations = (await session.execute(
        select(Observation)
        .where(Observation.patient_id == patient.resource_id)
        .order_by(Observation.effective_at.desc())
    )).scalars().all()
    conditions = (await session.execute(
        select(Condition)
        .where(Condition.patient_id == patient.resource_id)
        .order_by(Condition.onset_date.desc())
    )).scalars().all()
    medications = (await session.execute(
        select(MedicationRequest)
        .where(MedicationRequest.patient_id == patient.resource_id)
        .order_by(MedicationRequest.authored_on.desc())
    )).scalars().all()

    # Open findings -> quality flags per resource logical id.
    findings = (await session.execute(
        select(DqFinding).where(DqFinding.patient_id == patient.resource_id, DqFinding.review_status == "open")
    )).scalars().all()
    flags: dict[str, list[str]] = {}
    for f in findings:
        flags.setdefault(f.resource_logical_id, []).append(f.rule_id)

    entries: list[dict[str, Any]] = []
    for e in encounters:
        entries.append({
            "type": "Encounter", "id": e.logical_id,
            "date": e.period_start.isoformat() if e.period_start else None,
            "class": e.class_, "status": e.status, "display": "Encounter",
            "quality_flags": flags.get(e.logical_id, []),
        })
    for o in observations:
        entries.append({
            "type": "Observation", "id": o.logical_id,
            "date": o.effective_at.isoformat() if o.effective_at else None,
            "display": o.code_display, "value": o.value_quantity,
            "unit": o.value_unit, "interpretation": o.interpretation,
            "code": {"system": o.code_system, "value": o.code_value},
            "quality_flags": flags.get(o.logical_id, []),
        })
    for c in conditions:
        entries.append({
            "type": "Condition", "id": c.logical_id,
            "date": c.onset_date.isoformat() if c.onset_date else None,
            "display": c.code_display, "clinical_status": c.clinical_status,
            "quality_flags": flags.get(c.logical_id, []),
        })
    for m in medications:
        entries.append({
            "type": "MedicationRequest", "id": m.logical_id,
            "date": m.authored_on.isoformat() if m.authored_on else None,
            "display": m.dm_d_display, "status": m.status,
            "quality_flags": flags.get(m.logical_id, []),
        })

    entries.sort(key=lambda x: x.get("date") or "", reverse=True)

    return {
        "patient": _demographics(patient),
        "synthetic_data_notice": SYNTHETIC_NOTICE,
        "entries": entries[:count],
        "counts": {
            "encounters": len(encounters),
            "observations": len(observations),
            "conditions": len(conditions),
            "medications": len(medications),
        },
        "page": {"count": min(count, len(entries)), "next": None},
    }


@router.get("/{patient_id}/observations")
async def patient_observations(
    patient_id: str,
    session: SessionDep,
    user: Reader,
    code: str | None = None,
    date: str | None = None,
) -> list[dict[str, Any]]:
    patient = await _get_patient(session, patient_id)
    stmt = select(Observation).where(Observation.patient_id == patient.resource_id)
    if code:
        stmt = stmt.where(Observation.code_value == code)
    if date:
        stmt = stmt.where(Observation.effective_at >= date)
    rows = (await session.execute(stmt.order_by(Observation.effective_at.desc()))).scalars().all()
    return [
        {
            "id": o.logical_id, "code": o.code_value, "code_display": o.code_display,
            "value": o.value_quantity, "unit": o.value_unit,
            "interpretation": o.interpretation, "effective": o.effective_at.isoformat() if o.effective_at else None,
        }
        for o in rows
    ]


@router.get("/{patient_id}/conditions")
async def patient_conditions(patient_id: str, session: SessionDep, user: Reader) -> list[dict[str, Any]]:
    patient = await _get_patient(session, patient_id)
    rows = (await session.execute(
        select(Condition).where(Condition.patient_id == patient.resource_id).order_by(Condition.onset_date.desc())
    )).scalars().all()
    return [
        {"id": c.logical_id, "code": c.code_value, "display": c.code_display,
         "clinical_status": c.clinical_status, "onset": c.onset_date.isoformat() if c.onset_date else None}
        for c in rows
    ]


@router.get("/{patient_id}/medications")
async def patient_medications(patient_id: str, session: SessionDep, user: Reader) -> list[dict[str, Any]]:
    patient = await _get_patient(session, patient_id)
    rows = (await session.execute(
        select(MedicationRequest)
        .where(MedicationRequest.patient_id == patient.resource_id)
        .order_by(MedicationRequest.authored_on.desc())
    )).scalars().all()
    return [
        {"id": m.logical_id, "code": m.dm_d_code, "display": m.dm_d_display,
         "status": m.status, "authored_on": m.authored_on.isoformat() if m.authored_on else None}
        for m in rows
    ]


@router.get("/{patient_id}/$export")
async def patient_export(patient_id: str, session: SessionDep, user: Analyst) -> dict[str, Any]:
    await _get_patient(session, patient_id)
    return await export_patient_bundle(session, patient_id)
