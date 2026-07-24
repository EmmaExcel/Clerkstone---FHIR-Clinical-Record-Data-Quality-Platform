"""FHIR search over the stored resource store (source-of-truth JSONB).

Supports the FHIR search parameters ``_id``, ``_lastUpdated``, ``patient``,
``code``, ``date``, ``_count`` and ``_include`` over the common resource types.
The API layer wraps the result in a FHIR ``searchset`` Bundle.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import FhirResource

# Resource types that carry a ``subject`` reference (filtered by ``patient``).
_SUBJECT_TYPES = {
    "Observation", "Condition", "Encounter", "MedicationRequest",
    "AllergyIntolerance", "Procedure", "Immunization", "DiagnosticReport",
}

# Field searched for the ``code`` parameter, per resource type.
_CODE_FIELD = {
    "Observation": "code",
    "Condition": "code",
    "MedicationRequest": "medicationCodeableConcept",
}

# Field searched for the ``date`` parameter, per resource type.
_DATE_FIELD = {
    "Observation": "effectiveDateTime",
    "Condition": "onsetDateTime",
    "Encounter": "period.start",
    "MedicationRequest": "authoredOn",
}

_PREFIX_OPS = {"ge": ">=", "le": "<=", "gt": ">", "lt": "<", "eq": "=", "ne": "!="}


def _split_prefix(value: str) -> tuple[str | None, str]:
    for prefix in _PREFIX_OPS:
        if value.startswith(prefix):
            return prefix, value[len(prefix):]
    return None, value


def _parse_last_updated(value: str) -> tuple[str | None, str]:
    return _split_prefix(value)


def _code_filter(column, field: str, code: str):
    """``code`` matches any coding in ``<field>.coding[]`` (parameterised JSONPath)."""
    return func.jsonb_path_exists(
        column,
        cast(f"$.{field}.coding[*].code ? (@ == $code)", JSONPATH),
        literal({"code": code}, JSONB),
    )


def _date_filter(column, field: str, value: str):
    """``date`` compares the ISO string of ``<field>`` (lexicographic = chronological)."""
    prefix, raw = _split_prefix(value)
    field_json = column[field].astext
    if prefix is None:
        return field_json == raw
    op = _PREFIX_OPS[prefix]
    if op == "!=":
        return field_json != raw
    if op == ">=":
        return field_json >= raw
    if op == "<=":
        return field_json <= raw
    if op == ">":
        return field_json > raw
    return field_json < raw


async def search_resources(
    session: AsyncSession,
    resource_type: str,
    *,
    _id: str | None = None,
    _last_updated: str | None = None,
    patient: str | None = None,
    code: str | None = None,
    date: str | None = None,
    _count: int | None = None,
    _page: int = 0,
) -> tuple[list[FhirResource], int]:
    """Return ``(rows, total)`` for a resource-type search.

    ``_id`` accepts a comma-separated list of logical ids; ``_lastUpdated`` and
    ``date`` accept the FHIR prefixes ``ge|le|gt|lt|eq|ne`` (default exact).
    """
    settings = get_settings()
    count = min(_count or settings.max_page_size, settings.max_page_size)
    page = max(0, _page)

    stmt = select(FhirResource).where(FhirResource.resource_type == resource_type)

    if _id:
        ids = [i.strip() for i in _id.split(",") if i.strip()]
        stmt = stmt.where(FhirResource.logical_id.in_(ids))

    if _last_updated:
        prefix, raw = _parse_last_updated(_last_updated)
        col = FhirResource.last_updated
        if prefix is None:
            stmt = stmt.where(col == raw)
        elif prefix == "ge":
            stmt = stmt.where(col >= raw)
        elif prefix == "le":
            stmt = stmt.where(col <= raw)
        elif prefix == "gt":
            stmt = stmt.where(col > raw)
        elif prefix == "lt":
            stmt = stmt.where(col < raw)

    if patient and resource_type in _SUBJECT_TYPES:
        stmt = stmt.where(
            FhirResource.payload["subject"]["reference"].astext == f"Patient/{patient}"
        )

    if code and resource_type in _CODE_FIELD:
        stmt = stmt.where(_code_filter(FhirResource.payload, _CODE_FIELD[resource_type], code))

    if date and resource_type in _DATE_FIELD:
        stmt = stmt.where(_date_filter(FhirResource.payload, _DATE_FIELD[resource_type], date))

    total = await session.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ) or 0

    rows = (
        await session.execute(
            stmt.order_by(FhirResource.last_updated.desc()).offset(page * count).limit(count)
        )
    ).scalars().all()

    return list(rows), int(total)


async def fetch_referenced(
    session: AsyncSession, rows: list[FhirResource], include: str | None
) -> list[FhirResource]:
    """Resolve ``_include`` references (e.g. ``*``, ``Patient``, ``Observation:subject``)."""
    if not include:
        return []
    refs: set[tuple[str, str]] = set()
    for row in rows:
        payload = row.payload
        for field in ("subject", "encounter", "performer", "requester"):
            ref = (payload.get(field) or {}).get("reference")
            if ref and "/" in ref:
                rt, lid = ref.split("/", 1)
                if include in ("*", rt) or f"{row.resource_type}:{field}" == include:
                    refs.add((rt, lid))
    if not refs:
        return []
    conditions = []
    for rt, lid in refs:
        conditions.append(
            (FhirResource.resource_type == rt) & (FhirResource.logical_id == lid)
        )
    referenced_rows = (
        await session.execute(select(FhirResource).where(or_(*conditions)))
    ).scalars().all()
    return list(referenced_rows)


def as_searchset_bundle(
    resource_type: str, rows: list[FhirResource], total: int, included: list[FhirResource]
) -> dict[str, Any]:
    """Render a FHIR ``searchset`` Bundle."""
    entries = [
        {"fullUrl": f"urn:uuid:{r.logical_id}", "resource": r.payload}
        for r in rows
    ]
    for r in included:
        entries.append({"fullUrl": f"urn:uuid:{r.logical_id}", "resource": r.payload})
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": total,
        "entry": entries,
    }
