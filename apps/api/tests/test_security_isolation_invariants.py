"""Structural invariants that keep tenancy from eroding as the codebase grows.

The cross-tenant tests prove today's endpoints are safe. These prove that a
*future* model or repository cannot quietly opt out of isolation.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.roles import ASSIGNABLE_ORG_ROLES, ROLE_PERMISSIONS, Permission, Role
from app.db.base import Base
from app.db.mixins import TenantScoped
from app.models import PLATFORM_SCOPED_TABLES
from app.repositories.base import TenantScopedRepository


def test_every_table_is_either_tenant_scoped_or_explicitly_platform_scoped():
    """A new table must make a deliberate isolation decision.

    If this fails, add `TenantScoped` to the model, or — only if the table
    genuinely holds no customer data — add it to PLATFORM_SCOPED_TABLES with a
    comment explaining why.
    """
    undecided = []
    for mapper in Base.registry.mappers:
        model = mapper.class_
        table_name = model.__tablename__
        if table_name in PLATFORM_SCOPED_TABLES:
            continue
        if not issubclass(model, TenantScoped):
            undecided.append(f"{model.__name__} (table {table_name})")

    assert not undecided, (
        "These models are neither TenantScoped nor listed in "
        f"PLATFORM_SCOPED_TABLES: {undecided}"
    )


def test_tenant_scoped_models_all_carry_an_organisation_id_column():
    for mapper in Base.registry.mappers:
        model = mapper.class_
        if not issubclass(model, TenantScoped):
            continue
        assert "organisation_id" in mapper.columns, (
            f"{model.__name__} is TenantScoped but has no organisation_id column"
        )
        assert mapper.columns["organisation_id"].nullable is False, (
            f"{model.__name__}.organisation_id must be NOT NULL — a nullable tenant "
            f"key allows orphan rows that belong to no organisation"
        )


def test_repository_refuses_to_be_built_without_a_tenant_context(db: Session):
    from app.repositories.entities import SiteRepository

    with pytest.raises(TypeError, match="requires a TenantContext"):
        SiteRepository(db, None)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="requires a TenantContext"):
        SiteRepository(db, "not-a-context")  # type: ignore[arg-type]


def test_repository_refuses_models_that_are_not_tenant_scoped(db: Session, two_tenants):
    """Guards against wrapping e.g. User in a tenant repository and assuming
    it is filtered when it structurally cannot be."""
    from app.core.tenancy import Principal, TenantContext
    from app.models import User

    class BadRepository(TenantScopedRepository):
        model = User

    context = TenantContext(
        principal=Principal(user_id=two_tenants.a.admin.id, email="x@example.com", is_platform_admin=False),
        organisation_id=two_tenants.a.organisation.id,
        role=Role.ORG_ADMIN,
    )

    with pytest.raises(TypeError, match="not TenantScoped"):
        BadRepository(db, context)


# --- Role/permission model ------------------------------------------------


def test_every_role_has_a_permission_set():
    for role in Role:
        assert role in ROLE_PERMISSIONS, f"{role} has no permission mapping"


def test_oversight_roles_are_read_only():
    """An auditor who can edit the records they assess has no evidentiary
    value; the same reasoning applies to executive and read-only roles."""
    write_permissions = {
        Permission.ORG_MANAGE,
        Permission.MEMBERS_MANAGE,
        Permission.APPLICABILITY_MANAGE,
        Permission.OPERATIONS_MANAGE,
        Permission.PLATFORM_ADMIN,
    }
    for role in (Role.AUDITOR, Role.EXECUTIVE, Role.READ_ONLY):
        granted = ROLE_PERMISSIONS[role]
        assert granted == frozenset({Permission.ORG_READ}), (
            f"{role} should be read-only but grants {granted & write_permissions}"
        )


def test_platform_admin_is_not_assignable_as_an_organisation_role():
    """Otherwise an org admin could escalate themselves to cross-tenant access."""
    assert Role.PLATFORM_ADMIN not in ASSIGNABLE_ORG_ROLES


def test_only_platform_admin_holds_the_platform_permission():
    for role, permissions in ROLE_PERMISSIONS.items():
        if role is Role.PLATFORM_ADMIN:
            assert Permission.PLATFORM_ADMIN in permissions
        else:
            assert Permission.PLATFORM_ADMIN not in permissions, (
                f"{role} must not grant platform-wide access"
            )


def test_all_roles_can_read_within_their_organisation():
    for role in ROLE_PERMISSIONS:
        assert Permission.ORG_READ in ROLE_PERMISSIONS[role]
