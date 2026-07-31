from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.config import get_settings
from app.core.auth import CurrentUser, require_role
from app.db.models import AuditEvent
from app.dependencies import SessionDep

router = APIRouter(prefix="/audit", tags=["audit"])

Admin = Annotated[CurrentUser, Depends(require_role("admin"))]


def _clamp_count(count: int | None) -> int:
    settings = get_settings()
    if count is None or count < 1:
        return 20
    return min(count, settings.max_page_size)


@router.get("/events")
async def list_events(
    session: SessionDep,
    user: Admin,
    _count: int | None = Query(default=None),
    _page: int | None = Query(default=0),
) -> dict[str, Any]:
    count = _clamp_count(_count)
    page = max(0, _page or 0)

    total = await session.scalar(select(func.count()).select_from(AuditEvent))
    rows = (
        await session.execute(
            select(AuditEvent).order_by(AuditEvent.id.desc()).offset(page * count).limit(count)
        )
    ).scalars().all()

    return {
        "total": total or 0,
        "events": [
            {
                "id": str(r.id),
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                "actor": r.actor,
                "actor_role": r.actor_role,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "outcome": r.outcome,
                "request_id": r.request_id,
                "prev_hash": r.prev_hash,
                "event_hash": r.event_hash,
            }
            for r in rows
        ],
        "page": {"count": len(rows), "page": page, "next": (page + 1) if len(rows) == count else None},
    }
