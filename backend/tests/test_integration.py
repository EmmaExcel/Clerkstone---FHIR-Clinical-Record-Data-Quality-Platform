from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.db.models import (
    Condition,
    Encounter,
    FhirResource,
    MedicationRequest,
    Observation,
    Patient,
)
from app.domain.fhir.ingest import ingest_bundle
from app.domain.quality.runner import run_quality
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[2]


def _valid_bundle() -> dict:
    return json.loads((ROOT / "data/fixtures/valid/patients.json").read_text())


async def _count(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


@pytest.mark.asyncio
async def test_ingest_and_projections(session):
    result = await ingest_bundle(session, _valid_bundle(), uploaded_by="test")
    await session.flush()
    assert result.status == "accepted"
    assert result.accepted > 400

    assert await _count(session, Patient) == 20
    assert await _count(session, FhirResource) == result.accepted
    assert await _count(session, Encounter) > 0
    assert await _count(session, Observation) > 0
    assert await _count(session, Condition) > 0
    assert await _count(session, MedicationRequest) > 0


@pytest.mark.asyncio
async def test_clean_baseline_has_no_errors(session):
    await ingest_bundle(session, _valid_bundle(), uploaded_by="test")
    await session.flush()
    _run_id, findings = await run_quality(session, triggered_by="test", scope={"patients": "all"})
    errors = [f for f in findings if f["severity"] == "error"]
    assert errors == []


@pytest.mark.asyncio
async def test_idempotent_reingest(session):
    bundle = _valid_bundle()
    first = await ingest_bundle(session, bundle, uploaded_by="test")
    await session.flush()
    second = await ingest_bundle(session, bundle, uploaded_by="test")
    await session.flush()
    # Idempotent: the second ingest stores nothing new but is not an error.
    assert second.accepted == 0
    assert second.status == "accepted"
    # Re-ingesting the same bundle must not create duplicate resources.
    assert await _count(session, FhirResource) == first.accepted
