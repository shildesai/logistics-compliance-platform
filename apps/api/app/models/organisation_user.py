import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.roles import Role
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrganisationUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Membership of a user in an organisation, carrying exactly one role.

    This table *is* the authorisation source of truth: a request is allowed to
    act within an organisation only if a row here links the caller to it. It is
    not tenant-scoped via the TenantScoped mixin because it defines tenancy
    rather than being subject to it — it carries organisation_id explicitly.
    """

    __tablename__ = "organisation_users"
    __table_args__ = (
        UniqueConstraint("organisation_id", "user_id", name="uq_organisation_user"),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="organisation_role", native_enum=False), nullable=False
    )

    organisation: Mapped["Organisation"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
