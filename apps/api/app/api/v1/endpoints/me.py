"""Endpoints about the calling user, not about any one organisation.

`/me/organisations` is what drives the organisation switcher. It returns only
organisations the caller actually holds a membership in, which is what keeps
the switcher from becoming a directory of every tenant on the platform.
"""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentPrincipal, DbSession
from app.core.roles import ASSIGNABLE_ORG_ROLES, Role, permissions_for
from app.models import Organisation, OrganisationUser
from app.schemas.tenancy import (
    CurrentUserOut,
    MembershipOut,
    OrganisationSummary,
    RoleDescriptionOut,
)

router = APIRouter(tags=["me"])


def _memberships_for(db, principal) -> list[MembershipOut]:
    if principal.is_platform_admin:
        # Platform staff can act anywhere; surface every organisation so the
        # switcher is usable for support work. This is the one place a
        # cross-tenant listing is intentional.
        organisations = (
            db.execute(select(Organisation).order_by(Organisation.name)).scalars().all()
        )
        return [
            MembershipOut(
                organisation=OrganisationSummary.model_validate(org),
                role=Role.PLATFORM_ADMIN,
                permissions=sorted(permissions_for(Role.PLATFORM_ADMIN)),
            )
            for org in organisations
        ]

    memberships = (
        db.execute(
            select(OrganisationUser)
            .options(joinedload(OrganisationUser.organisation))
            .where(OrganisationUser.user_id == principal.user_id)
        )
        .scalars()
        .all()
    )
    return [
        MembershipOut(
            organisation=OrganisationSummary.model_validate(m.organisation),
            role=m.role,
            permissions=sorted(permissions_for(m.role)),
        )
        for m in sorted(memberships, key=lambda m: m.organisation.name)
    ]


@router.get("/me", response_model=CurrentUserOut)
def get_me(db: DbSession, principal: CurrentPrincipal) -> CurrentUserOut:
    from app.models import User

    user = db.execute(select(User).where(User.id == principal.user_id)).scalar_one()
    return CurrentUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_platform_admin=user.is_platform_admin,
        memberships=_memberships_for(db, principal),
    )


@router.get("/me/organisations", response_model=list[MembershipOut])
def list_my_organisations(db: DbSession, principal: CurrentPrincipal) -> list[MembershipOut]:
    return _memberships_for(db, principal)


@router.get("/roles", response_model=list[RoleDescriptionOut])
def list_roles() -> list[RoleDescriptionOut]:
    """The platform's fixed role catalogue and what each role grants."""
    return [
        RoleDescriptionOut(
            role=role,
            permissions=sorted(permissions_for(role)),
            assignable_in_organisation=role in ASSIGNABLE_ORG_ROLES,
        )
        for role in Role
    ]
