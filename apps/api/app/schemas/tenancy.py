import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.core.roles import Permission, Role
from app.models.accreditation import (
    AccreditationModule,
    AccreditationScheme,
    AccreditationStatus,
)
from app.models.organisation import OrganisationStatus
from app.models.site import SiteType
from app.models.supplier import SupplierType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Identity -------------------------------------------------------------


class OrganisationSummary(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    status: OrganisationStatus


class MembershipOut(BaseModel):
    organisation: OrganisationSummary
    role: Role
    permissions: list[Permission]


class CurrentUserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_platform_admin: bool
    memberships: list[MembershipOut]


class OrganisationMemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: Role


# --- Organisation profile -------------------------------------------------


class OrganisationProfileOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    legal_name: str | None
    abn: str | None
    status: OrganisationStatus


class OrganisationProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    abn: str | None = Field(default=None, max_length=20)


# --- Applicability: jurisdictions & CoR roles -----------------------------


class JurisdictionOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    hvnl_participant: bool


class OrganisationJurisdictionOut(BaseModel):
    id: uuid.UUID
    jurisdiction: JurisdictionOut


class JurisdictionAssignmentIn(BaseModel):
    jurisdiction_ids: list[uuid.UUID]


class CoRRoleOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None


class OrganisationCoRRoleOut(BaseModel):
    id: uuid.UUID
    cor_role: CoRRoleOut
    notes: str | None


class CoRRoleAssignmentIn(BaseModel):
    cor_role_ids: list[uuid.UUID]


# --- Accreditation --------------------------------------------------------


class AccreditationOut(ORMModel):
    id: uuid.UUID
    scheme: AccreditationScheme
    module: AccreditationModule
    status: AccreditationStatus
    accreditation_number: str | None
    valid_from: date | None
    valid_to: date | None
    notes: str | None


class AccreditationIn(BaseModel):
    scheme: AccreditationScheme
    module: AccreditationModule
    status: AccreditationStatus = AccreditationStatus.NOT_ACCREDITED
    accreditation_number: str | None = Field(default=None, max_length=100)
    valid_from: date | None = None
    valid_to: date | None = None
    notes: str | None = None


# --- Operational records --------------------------------------------------


class BusinessUnitOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    parent_id: uuid.UUID | None
    is_active: bool


class BusinessUnitIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    parent_id: uuid.UUID | None = None


class SiteOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    site_type: SiteType
    jurisdiction_id: uuid.UUID | None
    business_unit_id: uuid.UUID | None
    suburb: str | None
    postcode: str | None
    is_active: bool


class SiteIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    site_type: SiteType = SiteType.DEPOT
    jurisdiction_id: uuid.UUID | None = None
    business_unit_id: uuid.UUID | None = None
    address_line: str | None = None
    suburb: str | None = None
    postcode: str | None = None


class FleetOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    business_unit_id: uuid.UUID | None
    home_site_id: uuid.UUID | None
    vehicle_count: int
    is_active: bool


class FleetIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    business_unit_id: uuid.UUID | None = None
    home_site_id: uuid.UUID | None = None
    vehicle_count: int = Field(default=0, ge=0)


class SupplierOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    abn: str | None
    supplier_type: SupplierType
    is_active: bool


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    abn: str | None = Field(default=None, max_length=20)
    supplier_type: SupplierType = SupplierType.CARRIER


class RoleDescriptionOut(BaseModel):
    role: Role
    permissions: list[Permission]
    assignable_in_organisation: bool
