from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, require_role
from app.dependencies import TerminologyDep

router = APIRouter(prefix="/terminology", tags=["terminology"])

Reader = Annotated[CurrentUser, Depends(require_role("reader"))]


@router.get("/resolve")
async def resolve_code(
    terminology: TerminologyDep,
    user: Reader,
    system: str = Query(...),
    code: str = Query(...),
) -> dict:
    if terminology is None:
        return {"system": system, "code": code, "resolved": False, "reason": "no terminology backend configured"}
    result = terminology.resolve(system, code)
    if result is None:
        return {"system": system, "code": code, "resolved": False}
    return {
        "system": system,
        "code": code,
        "resolved": True,
        "display": result.get("display"),
        "active": result.get("active", True),
    }
