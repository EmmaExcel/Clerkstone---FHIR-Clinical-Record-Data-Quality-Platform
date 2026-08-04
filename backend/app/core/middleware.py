from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import get_settings
from app.core.audit import record_event
from app.core.auth import decode_token
from app.db.session import async_session_factory

_AUDIT_SKIP_PREFIXES = ("/health", "/ready", "/docs", "/openapi.json", "/redoc", "/metrics")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id

        actor, role = "anonymous", "reader"
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                claims = decode_token(auth[7:])
                actor = claims["sub"]
                role = claims.get("role", "reader")
            except Exception:  # noqa: BLE001, S110 — best-effort subject resolution
                pass

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Clerkstone-Data-Class"] = settings.data_class

        if not request.url.path.startswith(_AUDIT_SKIP_PREFIXES):
            outcome = "success"
            if response.status_code in (401, 403):
                outcome = "denied"
            elif response.status_code >= 400:
                outcome = "error"
            try:
                async with async_session_factory() as session:
                    await record_event(
                        session,
                        actor=actor,
                        actor_role=role,
                        action=f"{request.method} {request.url.path}",
                        outcome=outcome,
                        request_id=request_id,
                        ip=request.client.host if request.client else None,
                    )
                    await session.commit()
            except Exception:  # noqa: BLE001, S110 — audit must never break the response
                pass

        return response
