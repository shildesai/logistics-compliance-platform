"""Tenant context: the single object that says *who* is asking and *which
organisation* they are asking about.

Every tenant-scoped read or write in the application derives its filter from
this object. It is constructed only by the authentication/authorisation
dependency chain (see app/api/deps.py) after membership has been verified —
never from a value the client supplied directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.errors import AppError
from app.core.roles import Permission, Role, permissions_for


class TenantAccessDenied(AppError):
    """The principal is authenticated but not permitted to do this."""

    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(code="forbidden", message=message, status_code=403)


class CrossTenantAccess(AppError):
    """A tenant-scoped lookup resolved to another organisation's row.

    Deliberately reported as 404, not 403: a 403 would confirm that the
    requested id exists somewhere on the platform, which is itself a
    cross-tenant information leak.
    """

    def __init__(self, message: str = "Resource not found"):
        super().__init__(code="not_found", message=message, status_code=404)


@dataclass(frozen=True)
class Principal:
    """An authenticated user, independent of any organisation."""

    user_id: uuid.UUID
    email: str
    is_platform_admin: bool


@dataclass(frozen=True)
class TenantContext:
    """An authenticated user acting within one specific organisation."""

    principal: Principal
    organisation_id: uuid.UUID
    role: Role

    @property
    def user_id(self) -> uuid.UUID:
        return self.principal.user_id

    @property
    def permissions(self) -> frozenset[Permission]:
        if self.principal.is_platform_admin:
            return permissions_for(Role.PLATFORM_ADMIN)
        return permissions_for(self.role)

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions

    def require(self, permission: Permission) -> None:
        if not self.has(permission):
            raise TenantAccessDenied(
                f"Role {self.role.value} does not grant {permission.value}"
            )
