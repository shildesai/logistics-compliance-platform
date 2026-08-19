"""Control tests: how a control's operation is evaluated against evidence.

`rule_configuration` is the single most important design decision in this
module. Every threshold, window and comparison a test applies lives there as
versioned data — never as code, and never in the frontend. That gives three
properties the product depends on:

  * a threshold change is a new ControlTestVersion with its own effective
    window, so a past result stays interpretable against the rule that
    actually applied at the time;
  * legal thresholds are reviewable and approvable by a compliance specialist
    without a code deploy (CLAUDE.md: "Never hard-code legal thresholds into
    UI code"); and
  * the frontend can render the configuration but cannot evaluate it — the
    engine is server-side only.
"""

import uuid

from sqlalchemy import Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.graph_enums import TestType
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class ControlTest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stable identity of a test. Content lives in ControlTestVersion."""

    __tablename__ = "control_tests"

    test_code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    control: Mapped["Control"] = relationship(back_populates="tests")
    versions: Mapped[list["ControlTestVersion"]] = relationship(
        back_populates="control_test",
        cascade="all, delete-orphan",
        order_by="ControlTestVersion.version",
    )


class ControlTestVersion(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "control_test_versions"
    __table_args__ = (
        UniqueConstraint("control_test_id", "version", name="uq_control_test_version"),
    )

    control_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("control_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    #: Plain-language statement of what the test looks for. Documentation for
    #: reviewers — the executable definition is `rule_configuration`.
    test_logic_description: Mapped[str] = mapped_column(Text, nullable=False)

    #: Test type can legitimately change between versions: a check that starts
    #: as MANUAL often becomes DETERMINISTIC once the data source is connected,
    #: which is why this sits on the version rather than the container.
    test_type: Mapped[TestType] = mapped_column(
        SAEnum(TestType, name="control_test_type", native_enum=False),
        nullable=False,
        index=True,
    )

    #: The executable rule, as data. Shape varies by test_type; the engine
    #: dispatches on `rule_configuration["kind"]`. Example (DETERMINISTIC):
    #:   {
    #:     "kind": "threshold_exceeded",
    #:     "metric": "work_time_minutes_in_window",
    #:     "window_hours": 24,
    #:     "limit_minutes": 720,
    #:     "comparison": "gt"
    #:   }
    rule_configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    #: How a failure is graded. Severity is configuration, not a fixed column,
    #: because the same test can warrant different severities depending on the
    #: margin of exceedance. Example:
    #:   {
    #:     "default": "HIGH",
    #:     "escalations": [{"when": {"exceedance_pct_gte": 25}, "severity": "CRITICAL"}]
    #:   }
    severity_configuration: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    #: Whether a human must confirm before a result becomes a material finding.
    #: Always true for AI_ASSISTED tests — enforced in the service layer, since
    #: AI must never make a final compliance determination (CLAUDE.md 1–3).
    human_review_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    #: PSOE dimensions a failure of this test casts doubt on.
    psoe_impact: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)), nullable=False, default=list
    )

    change_note: Mapped[str | None] = mapped_column(Text)

    control_test: Mapped["ControlTest"] = relationship(back_populates="versions")
    evidence_requirements: Mapped[list["EvidenceRequirement"]] = relationship(
        back_populates="control_test_version", cascade="all, delete-orphan"
    )
    remediation_templates: Mapped[list["RemediationTemplate"]] = relationship(
        back_populates="control_test_version", cascade="all, delete-orphan"
    )
