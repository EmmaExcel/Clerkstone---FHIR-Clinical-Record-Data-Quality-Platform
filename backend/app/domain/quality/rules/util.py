from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.domain.fhir.resources import NHS_NUMBER_SYSTEM


def _as_datetime(value: str) -> datetime | None:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    dt = _as_datetime(value)
    if dt is not None:
        return dt.date()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    dt = _as_datetime(value)
    if dt is not None:
        return dt
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            d = datetime.strptime(value.strip(), fmt).date()
            return datetime.combine(d, datetime.min.time(), tzinfo=UTC)
        except ValueError:
            continue
    return None


def get_nhs_numbers(resource: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for ident in resource.get("identifier") or []:
        if (ident or {}).get("system") == NHS_NUMBER_SYSTEM and ident.get("value"):
            out.append(str(ident["value"]))
    return out


def codings_of(codeable: dict[str, Any] | None) -> list[dict[str, Any]]:
    return list((codeable or {}).get("coding") or [])


def has_code(resource: dict[str, Any], system: str, code: str) -> bool:
    for c in codings_of(resource.get("code")):
        if c.get("system") == system and c.get("code") == code:
            return True
    return False


def first_code(codeable: dict[str, Any] | None) -> dict[str, Any]:
    codings = codings_of(codeable)
    return codings[0] if codings else {}


def subject_reference(resource: dict[str, Any]) -> str | None:
    return (resource.get("subject") or {}).get("reference")
