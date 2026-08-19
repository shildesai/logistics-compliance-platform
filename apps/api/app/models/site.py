import uuid
from enum import StrEnum

from sqlalchemy import Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TenantScoped, TimestampMixin, UUIDPrimaryKeyMixin


class SiteType(StrEnum):
    DEPOT = "DEPOT"
    DISTRIBUTION_CENTRE = "DISTRIBUTION_CENTRE"
    LOADING_FACILITY = "LOADING_FACILITY"
    WORKSHOP = "WORKSHOP"
    CUSTOMER_SITE = "CUSTOMER_SITE"
    OTHER = "OTHER"


class Site(Base, UUIDPrimaryKeyMixin, TenantScoped, TimestampMixin):
    """A physical location an organisation operates from or into."""

    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("organisation_id", "code", name="uq_site_code"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    site_type: Mapped[SiteType] = mapped_column(
        SAEnum(SiteType, name="site_type", native_enum=False),
        default=SiteType.DEPOT,
        nullable=False,
    )
    # The jurisdiction a site sits in drives which rule pack applies to work
    # performed there.
    jurisdiction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id", ondelete="SET NULL"), index=True
    )
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL"), index=True
    )
    address_line: Mapped[str | None] = mapped_column(String(255))
    suburb: Mapped[str | None] = mapped_column(String(120))
    postcode: Mapped[str | None] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
