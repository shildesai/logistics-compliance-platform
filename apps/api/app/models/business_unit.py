import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TenantScoped, TimestampMixin, UUIDPrimaryKeyMixin


class BusinessUnit(Base, UUIDPrimaryKeyMixin, TenantScoped, TimestampMixin):
    """A division within an organisation (e.g. Bulk, Linehaul, Metro).

    May nest via `parent_id`. Nesting is constrained to the same organisation
    by the repository layer — a foreign key alone cannot express "parent must
    belong to the same tenant", so that check is explicit in the service.
    """

    __tablename__ = "business_units"
    __table_args__ = (
        UniqueConstraint("organisation_id", "code", name="uq_business_unit_code"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["BusinessUnit | None"] = relationship(remote_side="BusinessUnit.id")
