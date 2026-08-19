"""Authentication.

THIS IS NOT PRODUCTION AUTHENTICATION.

Phase 1 has no identity provider. To let tenancy be built and tested end to
end, the API accepts the caller's identity from an `X-User-Id` header. That is
obviously forgeable, so it is gated:

  * it only works when `auth_mode` is `dev_header`; and
  * the application refuses to start if `auth_mode` is `dev_header` while
    `environment` is a production-like value.

Replacing this with SSO/OIDC (see docs/TENANCY.md) means implementing
`resolve_principal` against a verified token. Nothing else in the codebase
needs to change: the rest of the system consumes `Principal`/`TenantContext`,
not headers.
"""

from __future__ import annotations

import uuid

from app.core.config import Settings

PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod", "staging"})

DEV_USER_HEADER = "X-User-Id"


class InsecureAuthConfiguration(RuntimeError):
    """Raised at startup if the dev auth shim is enabled outside development."""


def assert_auth_mode_is_safe(settings: Settings) -> None:
    if (
        settings.auth_mode == "dev_header"
        and settings.environment.lower() in PRODUCTION_ENVIRONMENTS
    ):
        raise InsecureAuthConfiguration(
            f"auth_mode='dev_header' is a development-only shim and must not be used "
            f"in environment='{settings.environment}'. Configure a real identity "
            f"provider before deploying."
        )


def parse_dev_user_id(raw: str | None) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None
