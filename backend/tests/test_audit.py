from __future__ import annotations

import pytest
from app.core.audit import record_event, verify_chain
from app.db.models import AuditEvent
from sqlalchemy import select


@pytest.mark.asyncio
async def test_chain_verifies(session):
    await record_event(session, actor="u1", actor_role="reader", action="read.patient", request_id="r1")
    await record_event(session, actor="u1", actor_role="reader", action="read.patient", request_id="r2")
    await session.flush()
    ok, bad_id = await verify_chain(session)
    assert ok is True and bad_id is None


@pytest.mark.asyncio
async def test_tamper_detected(session):
    await record_event(session, actor="u1", actor_role="reader", action="read.patient", request_id="r1")
    await session.flush()
    # Tamper: flip an action string in the first row.
    row = (await session.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars().first()
    row.action = "tampered"
    await session.flush()
    ok, bad_id = await verify_chain(session)
    assert ok is False and bad_id is not None


@pytest.mark.asyncio
async def test_ip_is_hashed(session):
    await record_event(session, actor="u1", actor_role="reader", action="read.patient", request_id="r1", ip="192.0.2.1")
    await session.flush()
    row = (await session.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars().first()
    assert row.ip_hash and row.ip_hash != "192.0.2.1"
