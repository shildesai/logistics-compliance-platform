import uuid
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrganisationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Organisation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tenant. The root of every operational record's ownership chain.

    Organisations are the isolation boundary: no query may return rows from
    more than one organisation unless the caller is a platform administrator.
    """

    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    # Australian Business Number. Stored as text: it is an identifier, not a
    # number, and leading zeros are significant.
    abn: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[OrganisationStatus] = mapped_column(
        SAEnum(OrganisationStatus, name="organisation_status", native_enum=False),
        default=OrganisationStatus.ACTIVE,
        nullable=False,
    )

    memberships: Mapped[list["OrganisationUser"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )
