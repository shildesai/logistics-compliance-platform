"""Remediation templates: the starting shape of a corrective action.

A template, not an instruction: it seeds a corrective action with sensible
defaults (owner archetype, due window, whether closure evidence and
effectiveness verification are needed). The operator still owns the actual
remediation decision — nothing here closes a finding automatically.
"""

import uuid

from sqlalchemy import Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.graph_enums import ControlOwnerType
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class RemediationTemplate(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "remediation_templates"
    __table_args__ = (
        UniqueConstraint(
            "template_code", "version", name="uq_remediation_template_version"
        ),
    )

    template_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    control_test_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("control_test_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    #: Ordered suggested actions. Guidance for the responsible person, not a
    #: workflow the system executes.
    suggested_steps: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )

    default_owner_type: Mapped[ControlOwnerType] = mapped_column(
        SAEnum(ControlOwnerType, name="control_owner_type", native_enum=False),
        nullable=False,
    )
    #: Days from raising to the default due date. Shorter for higher severity.
    default_due_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)

    #: Whether closing requires attached evidence. Corrective actions that can
    #: be closed on assertion alone are the failure mode this product exists
    #: to remove, so this defaults to true.
    requires_closure_evidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    #: Whether recurrence must be checked after closure before the control is
    #: treated as effective again.
    requires_effectiveness_check: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    control_test_version: Mapped["ControlTestVersion"] = relationship(
        back_populates="remediation_templates"
    )
