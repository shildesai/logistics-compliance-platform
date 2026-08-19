import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TenantScoped, TimestampMixin, UUIDPrimaryKeyMixin


class CoRRole(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A Chain of Responsibility party type under the HVNL.

    Platform-wide reference data (see Jurisdiction for why this is not
    tenant-scoped). An organisation may hold several of these simultaneously —
    CoR duties attach to what a party *does*, not to what it calls itself, and
    a business can be an employer, a scheduler and a consignor at once.
    """

    __tablename__ = "cor_roles"

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class OrganisationCoRRole(Base, UUIDPrimaryKeyMixin, TenantScoped, TimestampMixin):
    """A CoR party type an organisation has determined applies to it.

    Self-declared. The platform records the determination and the evidence
    trail around it; it does not make the legal determination itself
    (docs/DECISIONS.md: no AI or automated legal conclusions).
    """

    __tablename__ = "organisation_cor_roles"
    __table_args__ = (
        UniqueConstraint("organisation_id", "cor_role_id", name="uq_organisation_cor_role"),
    )

    cor_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cor_roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    cor_role: Mapped["CoRRole"] = relationship()
