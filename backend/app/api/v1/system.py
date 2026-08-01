from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.dependencies import SessionDep

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep) -> JSONResponse:
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False

    body = {"status": "ready" if db_ok else "unavailable", "db": db_ok}
    return JSONResponse(status_code=200 if db_ok else 503, content=body)
