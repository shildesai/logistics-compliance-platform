"""Organisation profile and applicability administration.

Every route here resolves a TenantContext first, so the organisation acted upon
is always one the caller has verified membership in — there is no path that
takes an organisation id straight from the request body.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentTenant, DbSession, require
from app.core.errors import AppError
from app.core.roles import Permission
from app.core.tenancy import TenantContext
from app.models import (
    Accreditation,
    CoRRole,
    Jurisdiction,
    Organisation,
    OrganisationCoRRole,
    OrganisationJurisdiction,
    OrganisationUser,
)
from app.repositories.entities import (
    AccreditationRepository,
    OrganisationCoRRoleRepository,
    OrganisationJurisdictionRepository,
)
from app.schemas.tenancy import (
    AccreditationIn,
    AccreditationOut,
    CoRRoleAssignmentIn,
    CoRRoleOut,
    JurisdictionAssignmentIn,
    JurisdictionOut,
    OrganisationCoRRoleOut,
    OrganisationJurisdictionOut,
    OrganisationMemberOut,
    OrganisationProfileOut,
    OrganisationProfileUpdate,
)

router = APIRouter(prefix="/organisation", tags=["organisation"])

ManageOrg = Annotated[TenantContext, Depends(require(Permission.ORG_MANAGE))]
ManageApplicability = Annotated[
    TenantContext, Depends(require(Permission.APPLICABILITY_MANAGE))
]
ManageMembers = Annotated[TenantContext, Depends(require(Permission.MEMBERS_MANAGE))]


def _load_organisation(db: DbSession, context: TenantContext) -> Organisation:
    return db.execute(
        select(Organisation).where(Organisation.id == context.organisation_id)
    ).scalar_one()


# --- Profile --------------------------------------------------------------


@router.get("", response_model=OrganisationProfileOut)
def get_profile(db: DbSession, context: CurrentTenant) -> Organisation:
    context.require(Permission.ORG_READ)
    return _load_organisation(db, context)


@router.patch("", response_model=OrganisationProfileOut)
def update_profile(
    db: DbSession, context: ManageOrg, payload: OrganisationProfileUpdate
) -> Organisation:
    org = _load_organisation(db, context)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    db.flush()
    return org


# --- Members --------------------------------------------------------------


@router.get("/members", response_model=list[OrganisationMemberOut])
def list_members(db: DbSession, context: CurrentTenant) -> list[OrganisationMemberOut]:
    context.require(Permission.ORG_READ)
    memberships = (
        db.execute(
            select(OrganisationUser)
            .options(joinedload(OrganisationUser.user))
            .where(OrganisationUser.organisation_id == context.organisation_id)
        )
        .scalars()
        .all()
    )
    return [
        OrganisationMemberOut(
            user_id=m.user.id,
            email=m.user.email,
            full_name=m.user.full_name,
            role=m.role,
        )
        for m in sorted(memberships, key=lambda m: m.user.full_name)
    ]


# --- Jurisdictions --------------------------------------------------------


@router.get("/jurisdictions", response_model=list[OrganisationJurisdictionOut])
def list_assigned_jurisdictions(
    db: DbSession, context: CurrentTenant
) -> list[OrganisationJurisdictionOut]:
    context.require(Permission.ORG_READ)
    rows = (
        db.execute(
            select(OrganisationJurisdiction)
            .options(joinedload(OrganisationJurisdiction.jurisdiction))
            .where(OrganisationJurisdiction.organisation_id == context.organisation_id)
        )
        .scalars()
        .all()
    )
    return [
        OrganisationJurisdictionOut(
            id=row.id, jurisdiction=JurisdictionOut.model_validate(row.jurisdiction)
        )
        for row in sorted(rows, key=lambda r: r.jurisdiction.code)
    ]


@router.put("/jurisdictions", response_model=list[OrganisationJurisdictionOut])
def set_assigned_jurisdictions(
    db: DbSession, context: ManageApplicability, payload: JurisdictionAssignmentIn
) -> list[OrganisationJurisdictionOut]:
    """Replace the organisation's jurisdiction assignments."""
    repo = OrganisationJurisdictionRepository(db, context)

    valid_ids = set(
        db.execute(
            select(Jurisdiction.id).where(Jurisdiction.id.in_(payload.jurisdiction_ids))
        )
        .scalars()
        .all()
    )
    requested = set(payload.jurisdiction_ids)
    unknown = requested - valid_ids
    if unknown:
        raise AppError(
            code="unknown_jurisdiction",
            message=f"Unknown jurisdiction id(s): {sorted(str(u) for u in unknown)}",
            status_code=422,
        )

    existing = {row.jurisdiction_id: row for row in repo.list()}

    for jurisdiction_id in requested - existing.keys():
        repo.add(OrganisationJurisdiction(jurisdiction_id=jurisdiction_id))
    for jurisdiction_id in existing.keys() - requested:
        repo.delete(existing[jurisdiction_id].id)

    db.flush()
    return list_assigned_jurisdictions(db, context)


@router.get("/jurisdictions/available", response_model=list[JurisdictionOut])
def list_available_jurisdictions(db: DbSession, context: CurrentTenant) -> list[Jurisdiction]:
    context.require(Permission.ORG_READ)
    return list(
        db.execute(select(Jurisdiction).order_by(Jurisdiction.code)).scalars().all()
    )


# --- CoR roles ------------------------------------------------------------


@router.get("/cor-roles", response_model=list[OrganisationCoRRoleOut])
def list_assigned_cor_roles(
    db: DbSession, context: CurrentTenant
) -> list[OrganisationCoRRoleOut]:
    context.require(Permission.ORG_READ)
    rows = (
        db.execute(
            select(OrganisationCoRRole)
            .options(joinedload(OrganisationCoRRole.cor_role))
            .where(OrganisationCoRRole.organisation_id == context.organisation_id)
        )
        .scalars()
        .all()
    )
    return [
        OrganisationCoRRoleOut(
            id=row.id,
            cor_role=CoRRoleOut.model_validate(row.cor_role),
            notes=row.notes,
        )
        for row in sorted(rows, key=lambda r: r.cor_role.name)
    ]


@router.put("/cor-roles", response_model=list[OrganisationCoRRoleOut])
def set_assigned_cor_roles(
    db: DbSession, context: ManageApplicability, payload: CoRRoleAssignmentIn
) -> list[OrganisationCoRRoleOut]:
    repo = OrganisationCoRRoleRepository(db, context)

    valid_ids = set(
        db.execute(select(CoRRole.id).where(CoRRole.id.in_(payload.cor_role_ids)))
        .scalars()
        .all()
    )
    requested = set(payload.cor_role_ids)
    unknown = requested - valid_ids
    if unknown:
        raise AppError(
            code="unknown_cor_role",
            message=f"Unknown CoR role id(s): {sorted(str(u) for u in unknown)}",
            status_code=422,
        )

    existing = {row.cor_role_id: row for row in repo.list()}

    for cor_role_id in requested - existing.keys():
        repo.add(OrganisationCoRRole(cor_role_id=cor_role_id))
    for cor_role_id in existing.keys() - requested:
        repo.delete(existing[cor_role_id].id)

    db.flush()
    return list_assigned_cor_roles(db, context)


@router.get("/cor-roles/available", response_model=list[CoRRoleOut])
def list_available_cor_roles(db: DbSession, context: CurrentTenant) -> list[CoRRole]:
    context.require(Permission.ORG_READ)
    return list(db.execute(select(CoRRole).order_by(CoRRole.name)).scalars().all())


# --- Accreditation --------------------------------------------------------


@router.get("/accreditations", response_model=list[AccreditationOut])
def list_accreditations(db: DbSession, context: CurrentTenant) -> list[Accreditation]:
    """Recorded accreditations.

    An empty list means "nothing recorded", not "non-compliant": heavy vehicle
    accreditation is voluntary. Callers must not render an empty result as a
    gap or finding. See app/models/accreditation.py.
    """
    context.require(Permission.ORG_READ)
    repo = AccreditationRepository(db, context)
    return list(repo.list(order_by=Accreditation.scheme))


@router.post("/accreditations", response_model=AccreditationOut, status_code=201)
def record_accreditation(
    db: DbSession, context: ManageApplicability, payload: AccreditationIn
) -> Accreditation:
    repo = AccreditationRepository(db, context)
    return repo.add(Accreditation(**payload.model_dump()))


@router.put("/accreditations/{accreditation_id}", response_model=AccreditationOut)
def update_accreditation(
    db: DbSession,
    context: ManageApplicability,
    accreditation_id: uuid.UUID,
    payload: AccreditationIn,
) -> Accreditation:
    repo = AccreditationRepository(db, context)
    record = repo.get(accreditation_id)
    for field, value in payload.model_dump().items():
        setattr(record, field, value)
    db.flush()
    return record


@router.delete("/accreditations/{accreditation_id}", status_code=204)
def delete_accreditation(
    db: DbSession, context: ManageApplicability, accreditation_id: uuid.UUID
) -> None:
    AccreditationRepository(db, context).delete(accreditation_id)
