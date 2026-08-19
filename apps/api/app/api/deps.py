"""Request dependencies: authentication, organisation resolution, permissions.

The chain is deliberately explicit:

    resolve_principal   — who is calling (dev shim; replace with OIDC)
        ↓
    resolve_tenant_context — which organisation, *verified against membership*
        ↓
    require(...)        — does that role grant this permission

The organisation is taken from the `X-Organisation-Id` header (or `?org=`), but
it is never trusted: `resolve_tenant_context` only returns a context after
finding an `OrganisationUser` row joining the caller to that organisation. A
caller naming an organisation they do not belong to gets 404 — not 403 — so the
response cannot be used to enumerate which organisations exist.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.roles import Permission, Role
from app.core.security import parse_dev_user_id
from app.core.tenancy import CrossTenantAccess, Principal, TenantContext
from app.db.session import get_db
from app.models import Organisation, OrganisationUser, User


class NotAuthenticated(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(code="unauthenticated", message=message, status_code=401)


def resolve_principal(
    db: Annotated[Session, Depends(get_db)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> Principal:
    user_id = parse_dev_user_id(x_user_id)
    if user_id is None:
        raise NotAuthenticated("Missing or malformed X-User-Id header")

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise NotAuthenticated("Unknown or inactive user")

    return Principal(
        user_id=user.id,
        email=user.email,
        is_platform_admin=user.is_platform_admin,
    )


CurrentPrincipal = Annotated[Principal, Depends(resolve_principal)]


def resolve_tenant_context(
    db: Annotated[Session, Depends(get_db)],
    principal: CurrentPrincipal,
    x_organisation_id: Annotated[str | None, Header(alias="X-Organisation-Id")] = None,
    org: Annotated[str | None, Query(description="Organisation id")] = None,
) -> TenantContext:
    raw = x_organisation_id or org
    if not raw:
        raise CrossTenantAccess("No organisation selected")

    try:
        organisation_id = uuid.UUID(raw)
    except ValueError:
        raise CrossTenantAccess("Organisation not found") from None

    membership = db.execute(
        select(OrganisationUser).where(
            OrganisationUser.organisation_id == organisation_id,
            OrganisationUser.user_id == principal.user_id,
        )
    ).scalar_one_or_none()

    if membership is None:
        # A platform administrator may act in any organisation, but only one
        # that actually exists, and the elevation is explicit here rather than
        # implied by a missing check.
        if not principal.is_platform_admin:
            raise CrossTenantAccess("Organisation not found")

        exists = db.execute(
            select(Organisation.id).where(Organisation.id == organisation_id)
        ).scalar_one_or_none()
        if exists is None:
            raise CrossTenantAccess("Organisation not found")
        return TenantContext(
            principal=principal,
            organisation_id=organisation_id,
            role=Role.PLATFORM_ADMIN,
        )

    return TenantContext(
        principal=principal,
        organisation_id=organisation_id,
        role=membership.role,
    )


CurrentTenant = Annotated[TenantContext, Depends(resolve_tenant_context)]
DbSession = Annotated[Session, Depends(get_db)]


def require(permission: Permission):
    """Dependency factory guarding a route with a required permission."""

    def _guard(context: CurrentTenant) -> TenantContext:
        context.require(permission)
        return context

    return _guard
