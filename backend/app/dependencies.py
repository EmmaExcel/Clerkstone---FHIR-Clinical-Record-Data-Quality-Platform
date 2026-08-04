from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain.fhir.validator import ValidatorClient, get_validator_client
from app.domain.quality.rules.base import TerminologyClient
from app.domain.terminology.base import get_terminology_client

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _terminology() -> TerminologyClient | None:
    return get_terminology_client()


TerminologyDep = Annotated[TerminologyClient | None, Depends(_terminology)]


def _validator() -> ValidatorClient | None:
    return get_validator_client()


ValidatorDep = Annotated[ValidatorClient | None, Depends(_validator)]
