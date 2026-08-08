from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.domain.fhir.ingest import ingest_bundle
from app.domain.fhir.search import (
    as_searchset_bundle,
    fetch_referenced,
    search_resources,
)

ROOT = Path(__file__).resolve().parents[2]


def _valid_bundle() -> dict:
    return json.loads((ROOT / "data/fixtures/valid/patients.json").read_text())


@pytest.mark.asyncio
async def test_search_by_type_and_count(session):
    await ingest_bundle(session, _valid_bundle(), uploaded_by="test")
    await session.flush()

    rows, total = await search_resources(session, "Patient", _count=5)
    assert total == 20
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_search_by_id(session):
    await ingest_bundle(session, _valid_bundle(), uploaded_by="test")
    await session.flush()

    rows, total = await search_resources(session, "Patient", _id="p-00000,p-00001")
    assert total == 2
    assert {r.logical_id for r in rows} == {"p-00000", "p-00001"}


@pytest.mark.asyncio
async def test_search_observation_by_patient_and_code(session):
    await ingest_bundle(session, _valid_bundle(), uploaded_by="test")
    await session.flush()

    rows, total = await search_resources(session, "Observation", patient="p-00000", code="271649006")
    assert total >= 1
    assert all(r.payload["subject"]["reference"] == "Patient/p-00000" for r in rows)


@pytest.mark.asyncio
async def test_search_date_prefix(session):
    await ingest_bundle(session, _valid_bundle(), uploaded_by="test")
    await session.flush()

    rows, total = await search_resources(session, "Observation", date="ge2026-01-01T00:00:00Z")
    assert total >= 1
    assert all((r.payload.get("effectiveDateTime") or "") >= "2026-01-01" for r in rows)


@pytest.mark.asyncio
async def test_search_include(session):
    await ingest_bundle(session, _valid_bundle(), uploaded_by="test")
    await session.flush()

    rows, _ = await search_resources(session, "Observation", patient="p-00000", _count=3)
    included = await fetch_referenced(session, rows, "Patient")
    assert included
    assert all(r.resource_type == "Patient" for r in included)

    bundle = as_searchset_bundle("Observation", rows, len(rows), included)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == len(rows)
