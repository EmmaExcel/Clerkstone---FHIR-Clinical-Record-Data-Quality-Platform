from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from app.api.errors import FhirError, operation_outcome
from app.core.auth import CurrentUser, require_role
from app.db.models import FhirResource
from app.dependencies import SessionDep, ValidatorDep
from app.domain.fhir.bundle import iter_entries
from app.domain.fhir.ingest import ingest_bundle
from app.domain.fhir.resources import resource_type_of
from app.domain.fhir.search import as_searchset_bundle, fetch_referenced, search_resources
from app.domain.fhir.validate import validate_payload

router = APIRouter(prefix="/fhir", tags=["fhir"])

Analyst = Annotated[CurrentUser, Depends(require_role("analyst"))]
Reader = Annotated[CurrentUser, Depends(require_role("reader"))]


@router.post("", status_code=201)
async def ingest(
    payload: dict[str, Any], session: SessionDep, user: Analyst
) -> dict[str, Any]:
    try:
        result = await ingest_bundle(session, payload, uploaded_by=user.subject)
    except (ValueError, PydanticValidationError) as exc:
        raise FhirError(400, "invalid", str(exc)) from exc
    await session.commit()
    return {
        "bundle_id": str(result.bundle_id),
        "status": result.status,
        "resources": {"accepted": result.accepted, "rejected": result.rejected},
        "errors": result.errors,
        "links": {"self": f"/api/v1/fhir/{result.bundle_id}"},
    }


@router.post("/$validate")
async def validate(payload: dict[str, Any], user: Reader, validator: ValidatorDep) -> dict[str, Any]:
    issues = validate_payload(payload)

    # UK Core profile validation via the sidecar (graceful fallback to structural).
    if validator is not None:
        resources = (
            [e.resource for e in iter_entries(payload)]
            if resource_type_of(payload) == "Bundle"
            else [payload]
        )
        sidecar_reachable = True
        for resource in resources:
            outcome = await validator.validate(resource)
            if outcome is None:
                sidecar_reachable = False
                break
            issues.extend(outcome.get("issue") or [])
        if not sidecar_reachable:
            issues.append(
                {
                    "severity": "warning",
                    "code": "informational",
                    "diagnostics": "Profile validation skipped: validator sidecar unreachable.",
                }
            )

    return operation_outcome(issues)


@router.get("/{resource_type}/{resource_id}")
async def read_resource(
    resource_type: str, resource_id: str, session: SessionDep, user: Reader
) -> dict[str, Any]:
    row = await session.scalar(
        select(FhirResource).where(
            FhirResource.resource_type == resource_type,
            FhirResource.logical_id == resource_id,
        )
    )
    if row is None:
        raise FhirError(404, "not-found", f"{resource_type}/{resource_id} not found")
    return row.payload


@router.get("/{resource_type}")
async def search_resource_type(
    resource_type: str,
    session: SessionDep,
    user: Reader,
    _id: str | None = None,
    _last_updated: str | None = None,
    patient: str | None = None,
    code: str | None = None,
    date: str | None = None,
    _count: int | None = None,
    _page: int = 0,
    _include: str | None = None,
) -> dict[str, Any]:
    rows, total = await search_resources(
        session,
        resource_type,
        _id=_id,
        _last_updated=_last_updated,
        patient=patient,
        code=code,
        date=date,
        _count=_count,
        _page=_page,
    )
    included = await fetch_referenced(session, rows, _include)
    return as_searchset_bundle(resource_type, rows, total, included)
