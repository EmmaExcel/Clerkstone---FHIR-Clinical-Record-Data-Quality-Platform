from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.domain.fhir.export import export_patient_bundle
from app.domain.fhir.ingest import ingest_bundle
from app.domain.quality.runner import run_quality
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]

_TRUNCATE = text(
    "TRUNCATE fhir_resource, ingestion_bundle, patient, encounter, observation, condition, "
    "medication_request, dq_run, dq_finding, dq_rule, dq_ruleset, review_task, audit_event CASCADE"
)


@pytest.mark.asyncio
async def test_roundtrip_no_new_findings(session, terminology):
    bundle = json.loads((ROOT / "data/fixtures/valid/patients.json").read_text())
    await ingest_bundle(session, bundle, uploaded_by="test")
    await session.flush()

    # Export one patient.
    exported = await export_patient_bundle(session, "p-00000")
    assert exported["resourceType"] == "Bundle"
    assert exported["entry"], "expected at least one exported resource"

    # Re-ingest into a fresh store.
    await session.execute(_TRUNCATE)
    await session.commit()
    result = await ingest_bundle(session, exported, uploaded_by="test")
    await session.flush()
    assert result.accepted == len(exported["entry"])

    # The exported resources were clean; re-ingesting must produce no new findings.
    _run_id, findings = await run_quality(
        session, triggered_by="test", scope={"patients": "all"}, terminology=terminology
    )
    errors = [f for f in findings if f["severity"] == "error"]
    assert errors == [], f"round-trip introduced error findings: {errors}"
