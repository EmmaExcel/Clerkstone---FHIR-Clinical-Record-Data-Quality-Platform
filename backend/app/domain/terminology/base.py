"""Terminology client factory — the dependency-injection seam.

``local`` resolves against a committed illustrative subset; ``nhse`` targets the
NHS England Terminology Server; ``offline-stub`` returns nothing (used when no
terminology is available). Swapping the live server in does not touch business
logic.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.domain.quality.rules.base import TerminologyClient


def get_terminology_client() -> TerminologyClient | None:
    settings = get_settings()
    backend = settings.terminology_backend.lower()
    if backend == "local":
        from app.domain.terminology.local import LocalTerminologyClient

        return LocalTerminologyClient(settings.terminology_local_db_path)
    if backend == "nhse":
        from app.domain.terminology.cache import CachedTerminologyClient
        from app.domain.terminology.nhse import NhseTerminologyClient

        inner = NhseTerminologyClient(
            base_url=settings.terminology_nhse_base_url,
            api_key=settings.terminology_nhse_api_key,
            circuit_breaker_threshold=settings.terminology_circuit_breaker_threshold,
        )
        return CachedTerminologyClient(inner, settings.terminology_cache_ttl_seconds)
    # offline-stub / unknown -> no resolution
    return None


__all__ = ["TerminologyClient", "get_terminology_client", "Any"]
