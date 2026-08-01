from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError as PydanticValidationError

from app.api.errors import FhirError
from app.core.auth import CurrentUser, require_role
from app.dependencies import SessionDep
from app.domain.fhir.ingest import ingest_bundle
from app.domain.hl7v2.to_fhir import adt_to_fhir_bundle

router = APIRouter(prefix="/hl7v2", tags=["hl7v2"])

Analyst = Annotated[CurrentUser, Depends(require_role("analyst"))]


@router.post("", status_code=201)
async def ingest_adt(request: Request, session: SessionDep, user: Analyst) -> dict[str, Any]:
    raw = await request.body()
    try:
        bundle = adt_to_fhir_bundle(raw.decode("utf-8"))
        result = await ingest_bundle(session, bundle, uploaded_by=user.subject)
    except (ValueError, PydanticValidationError) as exc:
        raise FhirError(400, "invalid", str(exc)) from exc
    await session.commit()
    return {
        "bundle_id": str(result.bundle_id),
        "status": result.status,
        "resources": {"accepted": result.accepted, "rejected": result.rejected},
    }
