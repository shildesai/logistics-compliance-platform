"""Evidence requirements: what data a control test needs in order to run.

Attached to ControlTestVersion rather than to the test container, because
changing what evidence a test needs *is* a change to the test and must be
versioned with it — otherwise a historical result could not be reproduced.
"""

import uuid

from sqlalchemy import Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.graph_enums import EvidenceSourceType
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class EvidenceRequirement(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "evidence_requirements"
    __table_args__ = (
        UniqueConstraint(
            "requirement_code", "version", name="uq_evidence_requirement_version"
        ),
    )

    requirement_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    control_test_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("control_test_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    source_type: Mapped[EvidenceSourceType] = mapped_column(
        SAEnum(EvidenceSourceType, name="evidence_source_type", native_enum=False),
        nullable=False,
    )
    #: Field names the test reads, e.g. ["driver_id", "work_start", "work_end"].
    #: Names the contract with the connector layer; ingestion that cannot
    #: supply these makes the test unrunnable rather than silently wrong.
    required_fields: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list
    )

    #: Whether the test can produce any result without this evidence. When a
    #: mandatory requirement is unmet the correct outcome is "not assessable",
    #: never "compliant" — absence of evidence is not evidence of compliance.
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    #: How stale the evidence may be before it stops supporting a conclusion.
    #: NULL means freshness is not a criterion for this requirement.
    max_age_days: Mapped[int | None] = mapped_column(Integer)

    retention_note: Mapped[str | None] = mapped_column(Text)

    control_test_version: Mapped["ControlTestVersion"] = relationship(
        back_populates="evidence_requirements"
    )
