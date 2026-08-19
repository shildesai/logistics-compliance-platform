"""Obligations: the plain-language duties a regulation imposes.

Obligations are versioned in place (each row *is* a version, identified by
`obligation_code` + `version`) rather than through a container/version split.
The split earns its keep only where other tables hold long-lived foreign keys
to the container; obligations are reached by traversal from a regulation, so a
second table would add joins without adding safety.

Obligations link to Regulation, not RegulationVersion: an obligation usually
survives an amendment untouched, and forcing a new obligation row for every
regulation version would churn the graph. Where an amendment *does* change the
duty, `RegulationVersion.requires_control_review` flags it for re-derivation.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class Obligation(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "obligations"
    __table_args__ = (
        UniqueConstraint("obligation_code", "version", name="uq_obligation_code_version"),
    )

    #: Stable identity across versions. Rows sharing this code are successive
    #: versions of the same duty.
    obligation_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    regulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    #: The duty stated in plain language, as an operator would read it.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    #: CoR party types this duty attaches to, e.g. ["OPERATOR", "SCHEDULER"].
    #: Matches CoRRole.code. Empty means it applies irrespective of CoR role.
    cor_role_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), nullable=False, default=list
    )

    regulation: Mapped["Regulation"] = relationship(back_populates="obligations")
    risks: Mapped[list["Risk"]] = relationship(
        back_populates="obligation", cascade="all, delete-orphan"
    )
    applicability_rules: Mapped[list["ApplicabilityRule"]] = relationship(
        back_populates="obligation", cascade="all, delete-orphan"
    )
