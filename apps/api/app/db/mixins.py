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
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.graph_enums import PUBLISHED_STATUSES, LifecycleStatus


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


class Versioned:
    """Effective-dated, governed record in the Compliance Control Graph.

    Regulatory content is never edited in place once it is in force: a change
    creates a new version with its own effective window, so an assessment made
    last year can still be shown against the rule that actually applied then
    (CLAUDE.md: "Never modify a regulatory rule without creating a new
    version"; "Regulatory rules must be versioned and effective-dated").

    `effective_to` is exclusive and nullable — NULL means "still in force".
    The invariants (no overlapping windows, immutability once in force) are
    enforced in app/services/versioning.py, because a database constraint
    cannot express them across the container/version split.
    """

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    status: Mapped[LifecycleStatus] = mapped_column(
        SAEnum(LifecycleStatus, name="lifecycle_status", native_enum=False),
        nullable=False,
        default=LifecycleStatus.DRAFT,
        index=True,
    )

    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    #: Exclusive upper bound. NULL = open-ended (currently in force).
    effective_to: Mapped[date | None] = mapped_column(Date, index=True)

    #: Citation for the authority this content derives from — a section
    #: reference, clause number or document identifier. Free text because
    #: source formats differ per regulator.
    source_reference: Mapped[str | None] = mapped_column(String(500))

    #: Governance trail. Nullable so drafts can exist before review; the
    #: service layer requires both to be set before a version becomes ACTIVE.
    @declared_attr
    @classmethod
    def reviewed_by_id(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
        )

    @declared_attr
    @classmethod
    def approved_by_id(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
        )

    def is_in_force_on(self, on: date) -> bool:
        """Whether this version governed the given date.

        Past tense deliberately: a SUPERSEDED version still governs dates
        inside its own window, because that is the rule an assessment made
        then was measured against. Restricting this to ACTIVE would make every
        historical query answer "no rule applied".

        The window is half-open — [effective_from, effective_to) — so a
        successor starting on the day its predecessor ends produces no
        ambiguity.
        """
        if self.status not in PUBLISHED_STATUSES:
            return False
        if on < self.effective_from:
            return False
        return self.effective_to is None or on < self.effective_to
