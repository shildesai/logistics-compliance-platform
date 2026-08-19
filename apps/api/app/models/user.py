from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A person's account.

    Users are deliberately NOT tenant-scoped: one person may hold membership in
    several organisations (a compliance adviser working across operators, an
    auditor engaged by multiple carriers). Their access to any given
    organisation comes from an OrganisationUser row, never from this table.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Platform staff. Grants cross-organisation access, so it lives on the user
    # account and can never be granted by an organisation administrator.
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    memberships: Mapped[list["OrganisationUser"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
