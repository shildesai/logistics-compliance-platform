"""Applicability rules: whether an obligation applies to a given operator.

The criteria are stored as data (`criteria` JSONB), not code, and are evaluated
server-side. Two reasons this is not negotiable:

  * CLAUDE.md — "Never hard-code legal thresholds into UI code." A jurisdiction
    list or accreditation condition living in a React component would be
    invisible to review, untestable, and unversioned.
  * Applicability is itself effective-dated. A rule that changes must produce a
    new version, which only works if the rule is a row rather than a branch in
    a function.

The frontend receives criteria purely as data to display. It never interprets
them; `POST /applicability/evaluate` is the only thing that decides.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class ApplicabilityRule(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "applicability_rules"
    __table_args__ = (
        UniqueConstraint("rule_code", "version", name="uq_applicability_rule_version"),
    )

    rule_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    obligation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("obligations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    #: Structured criteria evaluated by app/services/applicability.py. Shape:
    #:   {
    #:     "jurisdictions":  ["NSW", "VIC"],       # any-of; omit for all
    #:     "cor_roles":      ["OPERATOR"],          # any-of; omit for all
    #:     "vehicle_types":  ["HEAVY_RIGID"],       # any-of; omit for all
    #:     "operating_models": ["OWN_FLEET"],       # any-of; omit for all
    #:     "requires_accreditation": false          # omit when irrelevant
    #:   }
    #: An omitted key means "does not constrain", never "matches nothing" —
    #: the safer default for a duty is that it applies.
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    obligation: Mapped["Obligation"] = relationship(back_populates="applicability_rules")
