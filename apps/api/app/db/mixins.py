"""Shared column mixins.

`TenantScoped` is the marker that makes tenancy enforceable rather than
aspirational: it supplies the `organisation_id` column, and the tenant-scoped
repository refuses to operate on any model that does not carry it. A security
test walks the SQLAlchemy registry and asserts that every operational table is
either tenant-scoped or explicitly listed as platform-wide reference data, so a
new table cannot quietly be added without an isolation decision being made.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TenantScoped:
    """Every operational record belongs to exactly one organisation."""

    @declared_attr
    @classmethod
    def organisation_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
