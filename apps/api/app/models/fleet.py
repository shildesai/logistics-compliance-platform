import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TenantScoped, TimestampMixin, UUIDPrimaryKeyMixin


class Fleet(Base, UUIDPrimaryKeyMixin, TenantScoped, TimestampMixin):
    """A grouping of vehicles under common management.

    Individual vehicles are not modelled here: this platform is not the system
    of record for fleet assets (docs/DECISIONS.md §1.11). A Fleet is the
    organisational handle that vehicle evidence from a maintenance or telematics
    system will later be attributed to.
    """

    __tablename__ = "fleets"
    __table_args__ = (UniqueConstraint("organisation_id", "code", name="uq_fleet_code"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL"), index=True
    )
    home_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), index=True
    )
    # Indicative size for dashboards/pricing tiers; authoritative counts come
    # from the connected fleet system once integrations land.
    vehicle_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
