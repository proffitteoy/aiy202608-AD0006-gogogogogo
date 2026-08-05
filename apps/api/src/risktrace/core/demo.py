from uuid import UUID

from risktrace.core.config import get_settings


def get_demo_tenant_id() -> UUID:
    """Return the server-owned tenant scope used by the fixed demo context."""

    return get_settings().demo_tenant_id
