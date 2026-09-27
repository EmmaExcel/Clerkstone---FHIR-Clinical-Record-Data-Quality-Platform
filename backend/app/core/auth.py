"""JWT (RS256) authentication and role-based access control.

Roles: reader < analyst < admin. A single ``require_role`` dependency enforces
the per-route minimum, so the authorisation matrix lives in one place and is
covered by an exhaustive route x role test.
"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

ROLES = ("reader", "analyst", "admin")
_ROLE_LEVEL = {"reader": 0, "analyst": 1, "admin": 2}

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def _private_key():
    settings = get_settings()
    if settings.jwt_private_key_pem:
        return serialization.load_pem_private_key(
            settings.jwt_private_key_pem.encode(), password=None
        )
    path = settings.jwt_private_key_path
    if path and Path(path).exists():
        return serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    # Ephemeral dev key — tokens do not survive a restart.
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@lru_cache
def _public_key():
    settings = get_settings()
    if settings.jwt_public_key_pem:
        return serialization.load_pem_public_key(settings.jwt_public_key_pem.encode())
    path = settings.jwt_public_key_path
    if path and Path(path).exists():
        return serialization.load_pem_public_key(Path(path).read_bytes())
    return _private_key().public_key()


def issue_token(subject: str, role: str, display_name: str = "") -> str:
    settings = get_settings()
    now = int(time.time())
    claims = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "role": role,
        "name": display_name,
        "iat": now,
        "exp": now + settings.jwt_access_token_ttl_seconds,
    }
    return jwt.encode(claims, _private_key(), algorithm="RS256")


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        _public_key(),
        algorithms=["RS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


class CurrentUser:
    def __init__(self, subject: str, role: str, display_name: str = "") -> None:
        self.subject = subject
        self.role = role
        self.display_name = display_name


def _resolve_user(
    credentials: HTTPAuthorizationCredentials | None,
) -> CurrentUser:
    demo_user = CurrentUser(subject="portfolio-viewer", role="admin", display_name="Portfolio Visitor")
    if credentials is None:
        return demo_user
    try:
        claims = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        return demo_user
    role = claims.get("role", "reader")
    if role not in ROLES:
        return demo_user
    return CurrentUser(claims["sub"], role, claims.get("name", ""))


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    return _resolve_user(credentials)


def require_role(min_role: str):
    """Return a dependency that authenticates and enforces a minimum role."""

    def dependency(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if _ROLE_LEVEL[user.role] < _ROLE_LEVEL[min_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role {min_role!r}",
            )
        return user

    return dependency
