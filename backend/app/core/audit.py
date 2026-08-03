"""Append-only, hash-chained audit log.

Each event's hash is ``SHA256(prev_hash || canonical_json(event))``, making the
log tamper-evident. The application role has no UPDATE/DELETE grant on the
``audit_event`` table. ``verify_chain`` recomputes every hash and reports the
first divergent position.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import AuditEvent

_GENESIS = hashlib.sha256(b"clerkstone-audit-genesis").hexdigest()


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    salt = get_settings().audit_hash_salt
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


def _event_bytes(
    *,
    occurred_at: datetime,
    actor: str,
    actor_role: str,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    outcome: str,
    reason: str | None,
    request_id: str,
    ip_hash: str | None,
) -> bytes:
    payload = {
        "occurred_at": occurred_at.isoformat(),
        "actor": actor,
        "actor_role": actor_role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "reason": reason,
        "request_id": request_id,
        "ip_hash": ip_hash,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


async def _prev_hash(session: AsyncSession) -> str:
    result = await session.execute(
        select(AuditEvent.event_hash).order_by(AuditEvent.id.desc()).limit(1)
    )
    return result.scalar_one_or_none() or _GENESIS


async def record_event(
    session: AsyncSession,
    *,
    actor: str,
    actor_role: str,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    outcome: str = "success",
    reason: str | None = None,
    request_id: str = "",
    ip: str | None = None,
) -> AuditEvent:
    now = datetime.now(UTC)
    ip_hash = hash_ip(ip)
    prev = await _prev_hash(session)
    event_hash = hashlib.sha256(
        prev.encode()
        + _event_bytes(
            occurred_at=now,
            actor=actor,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            reason=reason,
            request_id=request_id,
            ip_hash=ip_hash,
        )
    ).hexdigest()

    event = AuditEvent(
        occurred_at=now,
        actor=actor,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        reason=reason,
        request_id=request_id,
        ip_hash=ip_hash,
        prev_hash=prev,
        event_hash=event_hash,
    )
    session.add(event)
    return event


async def verify_chain(session: AsyncSession) -> tuple[bool, int | None]:
    """Recompute the hash chain; return ``(valid, first_bad_id)``."""
    rows = (
        await session.execute(select(AuditEvent).order_by(AuditEvent.id))
    ).scalars().all()
    prev = _GENESIS
    for row in rows:
        expected = hashlib.sha256(
            prev.encode()
            + _event_bytes(
                occurred_at=row.occurred_at,
                actor=row.actor,
                actor_role=row.actor_role,
                action=row.action,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                outcome=row.outcome,
                reason=row.reason,
                request_id=row.request_id,
                ip_hash=row.ip_hash,
            )
        ).hexdigest()
        if expected != row.event_hash:
            return False, row.id
        prev = row.event_hash
    return True, None
