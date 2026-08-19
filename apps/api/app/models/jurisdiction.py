import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TenantScoped, TimestampMixin, UUIDPrimaryKeyMixin


class Jurisdiction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An Australian state or territory.

    Platform-wide reference data, deliberately NOT tenant-scoped: the set of
    jurisdictions is a fact about the country, identical for every tenant, and
    contains no customer information. Tenants attach themselves to
    jurisdictions via OrganisationJurisdiction.
    """

    __tablename__ = "jurisdictions"

    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # WA and NT are not participants in the Heavy Vehicle National Law; they
    # operate their own heavy-vehicle legislation. Rule packs for those
    # jurisdictions are explicitly out of scope (docs/DECISIONS.md §1.7), so
    # this flag exists to keep HVNL logic from being applied there by default.
    hvnl_participant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OrganisationJurisdiction(Base, UUIDPrimaryKeyMixin, TenantScoped, TimestampMixin):
    """A jurisdiction an organisation operates in."""

    __tablename__ = "organisation_jurisdictions"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id", "jurisdiction_id", name="uq_organisation_jurisdiction"
        ),
    )

    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    jurisdiction: Mapped["Jurisdiction"] = relationship()
