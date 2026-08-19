from enum import StrEnum

from sqlalchemy import Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TenantScoped, TimestampMixin, UUIDPrimaryKeyMixin


class SupplierType(StrEnum):
    CARRIER = "CARRIER"
    SUBCONTRACTOR = "SUBCONTRACTOR"
    OWNER_DRIVER = "OWNER_DRIVER"
    LABOUR_HIRE = "LABOUR_HIRE"
    MAINTENANCE_PROVIDER = "MAINTENANCE_PROVIDER"
    OTHER = "OTHER"


class Supplier(Base, UUIDPrimaryKeyMixin, TenantScoped, TimestampMixin):
    """A transport supplier engaged by this organisation.

    Note the tenancy subtlety: a supplier recorded here belongs to the engaging
    organisation's tenant. If that supplier is *also* a customer of the
    platform, it is a separate Organisation, and nothing here grants either
    party visibility of the other's data. Governed cross-tenant sharing (the
    Compliance Passport) is Phase 3 and deliberately not modelled yet —
    see docs/DECISIONS.md §1.12.
    """

    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("organisation_id", "code", name="uq_supplier_code"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    abn: Mapped[str | None] = mapped_column(String(20))
    supplier_type: Mapped[SupplierType] = mapped_column(
        SAEnum(SupplierType, name="supplier_type", native_enum=False),
        default=SupplierType.CARRIER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
