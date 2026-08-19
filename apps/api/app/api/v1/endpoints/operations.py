"""Operational reference records: business units, sites, fleets, suppliers.

Every record here is tenant-scoped. Reads go through the tenant repository so
they are filtered by organisation; writes go through `repo.add`, which stamps
the organisation from the verified context rather than the request body.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentTenant, DbSession, require
from app.core.roles import Permission
from app.core.tenancy import TenantContext
from app.models import BusinessUnit, Fleet, Site, Supplier
from app.repositories.entities import (
    BusinessUnitRepository,
    FleetRepository,
    SiteRepository,
    SupplierRepository,
)
from app.schemas.tenancy import (
    BusinessUnitIn,
    BusinessUnitOut,
    FleetIn,
    FleetOut,
    SiteIn,
    SiteOut,
    SupplierIn,
    SupplierOut,
)

router = APIRouter(tags=["operations"])

ManageOperations = Annotated[TenantContext, Depends(require(Permission.OPERATIONS_MANAGE))]


def _require_read(context: TenantContext) -> None:
    context.require(Permission.ORG_READ)


# --- Business units -------------------------------------------------------


@router.get("/business-units", response_model=list[BusinessUnitOut])
def list_business_units(db: DbSession, context: CurrentTenant) -> list[BusinessUnit]:
    _require_read(context)
    return list(BusinessUnitRepository(db, context).list(order_by=BusinessUnit.name))


@router.post("/business-units", response_model=BusinessUnitOut, status_code=201)
def create_business_unit(
    db: DbSession, context: ManageOperations, payload: BusinessUnitIn
) -> BusinessUnit:
    repo = BusinessUnitRepository(db, context)
    if payload.parent_id is not None:
        # A foreign key cannot express "parent must be in the same tenant";
        # resolving it through the scoped repository does, and raises 404 if
        # the parent belongs to another organisation.
        repo.get(payload.parent_id)
    return repo.add(BusinessUnit(**payload.model_dump()))


@router.get("/business-units/{business_unit_id}", response_model=BusinessUnitOut)
def get_business_unit(
    db: DbSession, context: CurrentTenant, business_unit_id: uuid.UUID
) -> BusinessUnit:
    _require_read(context)
    return BusinessUnitRepository(db, context).get(business_unit_id)


# --- Sites ----------------------------------------------------------------


@router.get("/sites", response_model=list[SiteOut])
def list_sites(db: DbSession, context: CurrentTenant) -> list[Site]:
    _require_read(context)
    return list(SiteRepository(db, context).list(order_by=Site.name))


@router.post("/sites", response_model=SiteOut, status_code=201)
def create_site(db: DbSession, context: ManageOperations, payload: SiteIn) -> Site:
    repo = SiteRepository(db, context)
    if payload.business_unit_id is not None:
        BusinessUnitRepository(db, context).get(payload.business_unit_id)
    return repo.add(Site(**payload.model_dump()))


@router.get("/sites/{site_id}", response_model=SiteOut)
def get_site(db: DbSession, context: CurrentTenant, site_id: uuid.UUID) -> Site:
    _require_read(context)
    return SiteRepository(db, context).get(site_id)


@router.delete("/sites/{site_id}", status_code=204)
def delete_site(db: DbSession, context: ManageOperations, site_id: uuid.UUID) -> None:
    SiteRepository(db, context).delete(site_id)


# --- Fleets ---------------------------------------------------------------


@router.get("/fleets", response_model=list[FleetOut])
def list_fleets(db: DbSession, context: CurrentTenant) -> list[Fleet]:
    _require_read(context)
    return list(FleetRepository(db, context).list(order_by=Fleet.name))


@router.post("/fleets", response_model=FleetOut, status_code=201)
def create_fleet(db: DbSession, context: ManageOperations, payload: FleetIn) -> Fleet:
    repo = FleetRepository(db, context)
    if payload.business_unit_id is not None:
        BusinessUnitRepository(db, context).get(payload.business_unit_id)
    if payload.home_site_id is not None:
        SiteRepository(db, context).get(payload.home_site_id)
    return repo.add(Fleet(**payload.model_dump()))


@router.get("/fleets/{fleet_id}", response_model=FleetOut)
def get_fleet(db: DbSession, context: CurrentTenant, fleet_id: uuid.UUID) -> Fleet:
    _require_read(context)
    return FleetRepository(db, context).get(fleet_id)


# --- Suppliers ------------------------------------------------------------


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: DbSession, context: CurrentTenant) -> list[Supplier]:
    _require_read(context)
    return list(SupplierRepository(db, context).list(order_by=Supplier.name))


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(
    db: DbSession, context: ManageOperations, payload: SupplierIn
) -> Supplier:
    return SupplierRepository(db, context).add(Supplier(**payload.model_dump()))


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(db: DbSession, context: CurrentTenant, supplier_id: uuid.UUID) -> Supplier:
    _require_read(context)
    return SupplierRepository(db, context).get(supplier_id)
