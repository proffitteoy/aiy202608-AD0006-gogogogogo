import hmac
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from risktrace.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class IngestionPrincipal:
    tenant_id: UUID
    allowed_providers: frozenset[str]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="valid ingestion bearer token required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_ingestion_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionPrincipal:
    if credentials is None:
        raise _unauthorized()

    expected_token = settings.ingestion_api_token.get_secret_value()
    allowed_providers = settings.ingestion_allowed_provider_set
    if not expected_token or not allowed_providers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ingestion authentication is not configured",
        )
    if not hmac.compare_digest(
        credentials.credentials.encode("utf-8"),
        expected_token.encode("utf-8"),
    ):
        raise _unauthorized()

    return IngestionPrincipal(
        tenant_id=settings.ingestion_tenant_id,
        allowed_providers=allowed_providers,
    )
