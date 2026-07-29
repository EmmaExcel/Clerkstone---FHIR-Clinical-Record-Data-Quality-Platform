from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DqFinding, DqRule, DqRuleset, DqRun, FhirResource, Patient
from app.domain.quality.engine import run_rules
from app.domain.quality.rules.base import TerminologyClient
from app.domain.quality.rules.registry import RULESET_VERSION, discover_rules, rule_catalog


async def ensure_ruleset(session: AsyncSession) -> str:
    """Seed the active ruleset and its rules; returns the ruleset version."""
    ruleset = await session.scalar(
        select(DqRuleset).where(DqRuleset.version == RULESET_VERSION)
    )
    if ruleset is None:
        ruleset = DqRuleset(version=RULESET_VERSION, rule_count=len(rule_catalog()))
        session.add(ruleset)
        await session.flush()
        for meta in rule_catalog():
            session.add(DqRule(ruleset_id=ruleset.id, enabled=True, **meta))
        await session.flush()
    return RULESET_VERSION


async def run_quality(
    session: AsyncSession,
    *,
    triggered_by: str,
    scope: dict[str, Any],
    terminology: TerminologyClient | None = None,
) -> tuple[uuid.UUID, list[dict[str, Any]]]:
    """Run the full ruleset over the store and persist findings.

    Returns ``(run_id, findings)`` where each finding is a serialisable dict.
    """
    await ensure_ruleset(session)

    run = DqRun(
        ruleset_version=RULESET_VERSION,
        triggered_by=triggered_by,
        scope=scope,
        status="running",
    )
    session.add(run)
    await session.flush()

    rows = (await session.execute(select(FhirResource))).scalars().all()
    resources = [r.payload for r in rows]
    reference_index = {f"{r.resource_type}/{r.logical_id}" for r in rows}
    resource_id_map = {(r.resource_type, r.logical_id): r.id for r in rows}
    patient_id_map = {r.logical_id: r.id for r in rows if r.resource_type == "Patient"}

    findings, _stats = run_rules(
        resources, discover_rules(), terminology=terminology, reference_index=reference_index
    )

    counts: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    serialised: list[dict[str, Any]] = []
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
        session.add(
            DqFinding(
                run_id=run.id,
                rule_id=f.rule_id,
                resource_id=resource_id_map.get((f.resource_type, f.resource_logical_id or "")),
                resource_logical_id=f.resource_logical_id or "",
                patient_id=patient_id_map.get(f.patient_logical_id) if f.patient_logical_id else None,
                expression=f.expression,
                message=f.message,
                severity=f.severity,
                context=f.context or None,
                review_status="open",
            )
        )
        serialised.append(
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "resource": {"type": f.resource_type, "logical_id": f.resource_logical_id},
                "patient_id": f.patient_logical_id,
                "expression": [f.expression],
                "message": f.message,
                "context": f.context,
                "suggested_action": f.suggested_action,
            }
        )

    run.status = "complete"
    run.finished_at = datetime.now(UTC)
    run.counts = counts
    await session.flush()

    return run.id, serialised


async def seed_patient_rules_context(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Helper: logical patient id -> patient row id, for finding FKs."""
    rows = (await session.execute(select(Patient.resource_id, Patient.logical_id))).all()
    return {logical: rid for rid, logical in rows}
