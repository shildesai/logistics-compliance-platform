"""ORM models.

`PLATFORM_SCOPED_TABLES` is the explicit allow-list of tables that legitimately
hold no `organisation_id`. Everything else must be tenant-scoped. A security
test walks the SQLAlchemy registry and fails if a new table appears in neither
category, so isolation cannot be forgotten when a model is added.
"""

from app.models.accreditation import (
    Accreditation,
    AccreditationModule,
    AccreditationScheme,
    AccreditationStatus,
)
from app.models.business_unit import BusinessUnit
from app.models.cor_role import CoRRole, OrganisationCoRRole
from app.models.fleet import Fleet
from app.models.jurisdiction import Jurisdiction, OrganisationJurisdiction
from app.models.organisation import Organisation, OrganisationStatus
from app.models.organisation_user import OrganisationUser
from app.models.site import Site, SiteType
from app.models.supplier import Supplier, SupplierType
from app.models.user import User

#: Tables that intentionally hold no organisation_id.
PLATFORM_SCOPED_TABLES: frozenset[str] = frozenset(
    {
        # The tenants themselves.
        "organisations",
        # Accounts are global; access comes from organisation_users.
        "users",
        # Membership defines tenancy rather than being subject to it (it does
        # carry organisation_id, but is not a TenantScoped operational record).
        "organisation_users",
        # Country-level reference data, identical for every tenant and
        # containing no customer information.
        "jurisdictions",
        "cor_roles",
        # Alembic bookkeeping.
        "alembic_version",
    }
)

__all__ = [
    "Accreditation",
    "AccreditationModule",
    "AccreditationScheme",
    "AccreditationStatus",
    "BusinessUnit",
    "CoRRole",
    "Fleet",
    "Jurisdiction",
    "Organisation",
    "OrganisationCoRRole",
    "OrganisationJurisdiction",
    "OrganisationStatus",
    "OrganisationUser",
    "PLATFORM_SCOPED_TABLES",
    "Site",
    "SiteType",
    "Supplier",
    "SupplierType",
    "User",
]
