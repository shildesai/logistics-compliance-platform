"""Concrete tenant-scoped repositories.

Each is a thin binding of the model to TenantScopedRepository; the isolation
logic lives entirely in the base class so it cannot diverge per entity.
"""

from app.models import (
    Accreditation,
    BusinessUnit,
    Fleet,
    OrganisationCoRRole,
    OrganisationJurisdiction,
    Site,
    Supplier,
)
from app.repositories.base import TenantScopedRepository


class SiteRepository(TenantScopedRepository[Site]):
    model = Site


class BusinessUnitRepository(TenantScopedRepository[BusinessUnit]):
    model = BusinessUnit


class FleetRepository(TenantScopedRepository[Fleet]):
    model = Fleet


class SupplierRepository(TenantScopedRepository[Supplier]):
    model = Supplier


class AccreditationRepository(TenantScopedRepository[Accreditation]):
    model = Accreditation


class OrganisationJurisdictionRepository(TenantScopedRepository[OrganisationJurisdiction]):
    model = OrganisationJurisdiction


class OrganisationCoRRoleRepository(TenantScopedRepository[OrganisationCoRRole]):
    model = OrganisationCoRRole
