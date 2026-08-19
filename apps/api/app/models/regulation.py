"""Regulations and the sources they are derived from.

The container/version split used here (Regulation + RegulationVersion) applies
wherever a record needs a stable identity that outlives its content: control
tests, findings and audit packs reference the *regulation*, while the text they
were assessed against is the *version*. Amending the law therefore adds a
version without invalidating every reference to it.
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class RegulatorySource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A citable published document a regulation version derives from.

    Kept separate from RegulationVersion so several versions (and several
    regulations) can cite the same publication, and so the retrieval date is
    recorded — regulator websites change, and an assurance claim needs to say
    what was read and when.
    """

    __tablename__ = "regulatory_sources"

    source_code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000))
    document_type: Mapped[str | None] = mapped_column(String(100))
    #: When this source was last read. Not the document's own publication date.
    retrieved_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class Regulation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stable identity of a body of law. Content lives in RegulationVersion."""

    __tablename__ = "regulations"

    regulation_code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100))
    #: Issuing body, e.g. NHVR. Jurisdictional applicability is expressed per
    #: version, because which states adopt a law can change over time.
    regulator: Mapped[str | None] = mapped_column(String(255))

    versions: Mapped[list["RegulationVersion"]] = relationship(
        back_populates="regulation",
        cascade="all, delete-orphan",
        order_by="RegulationVersion.version",
    )
    obligations: Mapped[list["Obligation"]] = relationship(back_populates="regulation")


class RegulationVersion(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "regulation_versions"
    __table_args__ = (
        UniqueConstraint("regulation_id", "version", name="uq_regulation_version"),
    )

    regulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    regulatory_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulatory_sources.id", ondelete="SET NULL")
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    #: Jurisdiction codes this version applies in, e.g. ["NSW", "VIC"]. WA and
    #: NT run separate heavy-vehicle legislation and are normally absent — see
    #: docs/DECISIONS.md §1.7.
    jurisdiction_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String(10)), nullable=False, default=list
    )
    #: Whether an amendment changed obligations materially enough that mapped
    #: controls should be re-reviewed rather than carried forward silently.
    requires_control_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    change_note: Mapped[str | None] = mapped_column(Text)

    regulation: Mapped["Regulation"] = relationship(back_populates="versions")
    regulatory_source: Mapped["RegulatorySource | None"] = relationship()
