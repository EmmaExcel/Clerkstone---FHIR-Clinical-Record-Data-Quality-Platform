from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.errors import FhirError
from app.config import get_settings
from app.core.auth import CurrentUser, require_role
from app.db.models import DqFinding, DqRule, DqRun, ReviewTask
from app.dependencies import SessionDep, TerminologyDep
from app.domain.quality.review import apply_transition
from app.domain.quality.runner import ensure_ruleset, run_quality

router = APIRouter(prefix="/quality", tags=["quality"])

Reader = Annotated[CurrentUser, Depends(require_role("reader"))]
Analyst = Annotated[CurrentUser, Depends(require_role("analyst"))]


def _clamp_count(count: int | None) -> int:
    settings = get_settings()
    if count is None or count < 1:
        return 20
    return min(count, settings.max_page_size)


@router.get("/rules")
async def list_rules(session: SessionDep, user: Reader) -> dict[str, Any]:
    await ensure_ruleset(session)
    rules = (await session.execute(select(DqRule).where(DqRule.enabled))).scalars().all()
    return {
        "count": len(rules),
        "rules": [
            {
                "id": r.id, "category": r.category, "severity": r.severity,
                "title": r.title, "description": r.description, "fhirpath": r.fhirpath,
            }
            for r in rules
        ],
    }


@router.post("/runs", status_code=201)
async def start_run(
    session: SessionDep,
    user: Analyst,
    terminology: TerminologyDep,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id, _findings = await run_quality(
        session, triggered_by=user.subject, scope=scope or {"patients": "all"}, terminology=terminology
    )
    await session.commit()
    return {"run_id": str(run_id), "links": {"self": f"/api/v1/quality/runs/{run_id}"}}


@router.get("/runs")
async def list_runs(
    session: SessionDep,
    user: Reader,
    _count: int | None = Query(default=None),
    _page: int | None = Query(default=0),
) -> dict[str, Any]:
    count = _clamp_count(_count)
    page = max(0, _page or 0)

    total = await session.scalar(select(func.count()).select_from(DqRun))
    rows = (
        await session.execute(
            select(DqRun).order_by(DqRun.started_at.desc()).offset(page * count).limit(count)
        )
    ).scalars().all()

    return {
        "total": total or 0,
        "runs": [
            {
                "id": str(r.id), "ruleset_version": r.ruleset_version,
                "triggered_by": r.triggered_by, "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "counts": r.counts,
            }
            for r in rows
        ],
        "page": {"count": len(rows), "page": page, "next": (page + 1) if len(rows) == count else None},
    }


@router.get("/runs/{run_id}")
async def run_summary(run_id: str, session: SessionDep, user: Reader) -> dict[str, Any]:
    run = await session.get(DqRun, run_id)
    if run is None:
        raise FhirError(404, "not-found", f"quality run {run_id} not found")
    return {
        "id": str(run.id), "ruleset_version": run.ruleset_version,
        "status": run.status, "triggered_by": run.triggered_by,
        "counts": run.counts,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("/runs/{run_id}/findings")
async def run_findings(
    run_id: str,
    session: SessionDep,
    user: Reader,
    severity: str | None = None,
    rule: str | None = None,
    _count: int | None = Query(default=None),
    _page: int | None = Query(default=0),
) -> dict[str, Any]:
    run = await session.get(DqRun, run_id)
    if run is None:
        raise FhirError(404, "not-found", f"quality run {run_id} not found")

    stmt = select(DqFinding).where(DqFinding.run_id == run.id)
    if severity:
        stmt = stmt.where(DqFinding.severity == severity)
    if rule:
        stmt = stmt.where(DqFinding.rule_id == rule)

    rule_map = {r.id: r for r in (await session.execute(select(DqRule))).scalars().all()}
    rows = (await session.execute(stmt.order_by(DqFinding.severity, DqFinding.rule_id))).scalars().all()

    counts: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    findings: list[dict[str, Any]] = []
    for f in rows:
        counts[f.severity] = counts.get(f.severity, 0) + 1
        rule_meta = rule_map.get(f.rule_id)
        findings.append({
            "id": str(f.id), "rule_id": f.rule_id,
            "severity": f.severity, "title": rule_meta.title if rule_meta else f.rule_id,
            "resource": {"logical_id": f.resource_logical_id},
            "patient_id": str(f.patient_id) if f.patient_id else None,
            "expression": [f.expression], "message": f.message,
            "context": f.context,
            "suggested_action": rule_meta.suggested_action if rule_meta else "",
            "review_status": f.review_status,
        })

    return {"run_id": str(run.id), "ruleset_version": run.ruleset_version,
            "summary": counts, "findings": findings}


@router.post("/findings/{finding_id}/assign")
async def assign_finding(finding_id: str, session: SessionDep, user: Analyst) -> dict[str, Any]:
    finding = await session.get(DqFinding, finding_id)
    if finding is None:
        raise FhirError(404, "not-found", f"finding {finding_id} not found")
    try:
        finding.review_status = apply_transition(finding.review_status, "assigned")
    except ValueError as exc:
        raise FhirError(409, "conflict", str(exc)) from exc
    task = await session.scalar(select(ReviewTask).where(ReviewTask.finding_id == finding.id))
    if task is None:
        task = ReviewTask(finding_id=finding.id)
        session.add(task)
    task.assigned_to = user.subject
    task.assigned_at = datetime.now(UTC)
    await session.commit()
    return {"id": str(finding.id), "review_status": "assigned", "assigned_to": user.subject}


@router.post("/findings/{finding_id}/resolve")
async def resolve_finding(
    finding_id: str, session: SessionDep, user: Analyst, resolution: str = "resolved"
) -> dict[str, Any]:
    finding = await session.get(DqFinding, finding_id)
    if finding is None:
        raise FhirError(404, "not-found", f"finding {finding_id} not found")
    target = "resolved" if resolution == "resolved" else "accepted_risk"
    try:
        finding.review_status = apply_transition(finding.review_status, target)
    except ValueError as exc:
        raise FhirError(409, "conflict", str(exc)) from exc
    task = await session.scalar(select(ReviewTask).where(ReviewTask.finding_id == finding.id))
    if task is not None:
        task.resolution = resolution
        task.resolved_at = datetime.now(UTC)
    await session.commit()
    return {"id": str(finding.id), "review_status": finding.review_status}
