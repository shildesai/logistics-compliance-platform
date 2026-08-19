"""Risks: the unsafe or non-compliant outcomes an obligation guards against."""

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.graph_enums import RiskConsequence, RiskLikelihood
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class Risk(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "risks"
    __table_args__ = (UniqueConstraint("risk_code", "version", name="uq_risk_code_version"),)

    risk_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    obligation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("obligations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    #: Inherent (pre-control) rating. Residual risk is an operator-specific
    #: assessment and does not belong in shared reference data.
    inherent_likelihood: Mapped[RiskLikelihood | None] = mapped_column(
        SAEnum(RiskLikelihood, name="risk_likelihood", native_enum=False)
    )
    inherent_consequence: Mapped[RiskConsequence | None] = mapped_column(
        SAEnum(RiskConsequence, name="risk_consequence", native_enum=False)
    )

    obligation: Mapped["Obligation"] = relationship(back_populates="risks")
    control_links: Mapped[list["ControlRiskLink"]] = relationship(
        back_populates="risk", cascade="all, delete-orphan"
    )
