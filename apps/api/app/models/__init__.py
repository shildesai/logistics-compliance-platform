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
from app.models.applicability_rule import ApplicabilityRule
from app.models.business_unit import BusinessUnit
from app.models.catalogue_import import CatalogueImportRecord
from app.models.control import Control, ControlRiskLink, ControlVersion
from app.models.control_test import ControlTest, ControlTestVersion
from app.models.cor_role import CoRRole, OrganisationCoRRole
from app.models.evidence_requirement import EvidenceRequirement
from app.models.fleet import Fleet
from app.models.jurisdiction import Jurisdiction, OrganisationJurisdiction
from app.models.obligation import Obligation
from app.models.organisation import Organisation, OrganisationStatus
from app.models.organisation_user import OrganisationUser
from app.models.regulation import Regulation, RegulationVersion, RegulatorySource
from app.models.remediation_template import RemediationTemplate
from app.models.risk import Risk
from app.models.site import Site, SiteType
from app.models.supplier import Supplier, SupplierType
from app.models.user import User

#: The Compliance Control Graph. Shared regulatory reference data, identical
#: for every tenant and containing no customer information: HVNL obligations
#: and the controls mapped to them do not differ per operator. Keeping it
#: platform-scoped is what allows one control assessment to serve many
#: obligations, and it is the platform's own IP rather than any customer's.
#:
#: Customer-specific obligations (contract terms a shipper imposes on a
#: carrier) are a Phase 3 concern and will be tenant-scoped records that
#: *reference* this graph — not additions to it. See docs/DECISIONS.md §1.12.
CONTROL_GRAPH_TABLES: frozenset[str] = frozenset(
    {
        "regulatory_sources",
        "regulations",
        "regulation_versions",
        "obligations",
        "risks",
        "controls",
        "control_versions",
        "control_risk_links",
        "control_tests",
        "control_test_versions",
        "evidence_requirements",
        "applicability_rules",
        "remediation_templates",
        # Provenance for content imported into the graph above. Platform-scoped
        # for the same reason the graph is: it describes shared reference data,
        # not any customer's records.
        "catalogue_import_records",
    }
)

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
) | CONTROL_GRAPH_TABLES

__all__ = [
    "Accreditation",
    "AccreditationModule",
    "AccreditationScheme",
    "AccreditationStatus",
    "ApplicabilityRule",
    "BusinessUnit",
    "CatalogueImportRecord",
    "CONTROL_GRAPH_TABLES",
    "Control",
    "ControlRiskLink",
    "ControlTest",
    "ControlTestVersion",
    "ControlVersion",
    "CoRRole",
    "EvidenceRequirement",
    "Fleet",
    "Jurisdiction",
    "Obligation",
    "Organisation",
    "OrganisationCoRRole",
    "OrganisationJurisdiction",
    "OrganisationStatus",
    "OrganisationUser",
    "PLATFORM_SCOPED_TABLES",
    "Regulation",
    "RegulationVersion",
    "RegulatorySource",
    "RemediationTemplate",
    "Risk",
    "Site",
    "SiteType",
    "Supplier",
    "SupplierType",
    "User",
]
