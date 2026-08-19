"""Controls: what an operator does to manage a risk.

Control uses the container/version split because control identity is
long-lived and widely referenced — findings, corrective actions and audit
workpapers all point at a control and must keep pointing at it across revisions
of its wording, owner or frequency.

Controls link to risks many-to-many. This is not gold-plating: the source
blueprint calls for a "shared-control architecture" where one control supports
several obligations, and in practice one fatigue-monitoring control mitigates
several distinct risks while one risk needs several controls. Modelling it as a
single FK would force duplicate control records and break the "assess once,
satisfy many" property the product is built on.
"""

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.graph_enums import AutomationLevel, ControlFrequency, ControlOwnerType
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin, Versioned


class Control(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stable identity of a control. Content lives in ControlVersion."""

    __tablename__ = "controls"

    control_code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    #: Domain grouping, e.g. "Fatigue / Work-Rest". Mirrors the control-test
    #: catalogue's domains so the two can be reconciled.
    domain: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    versions: Mapped[list["ControlVersion"]] = relationship(
        back_populates="control",
        cascade="all, delete-orphan",
        order_by="ControlVersion.version",
    )
    tests: Mapped[list["ControlTest"]] = relationship(back_populates="control")
    risk_links: Mapped[list["ControlRiskLink"]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )


class ControlVersion(Base, UUIDPrimaryKeyMixin, Versioned, TimestampMixin):
    __tablename__ = "control_versions"
    __table_args__ = (
        UniqueConstraint("control_id", "version", name="uq_control_version"),
    )

    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    #: What the control is meant to achieve — the assurance question it
    #: answers, not the procedure for doing it.
    objective: Mapped[str] = mapped_column(Text, nullable=False)

    owner_type: Mapped[ControlOwnerType] = mapped_column(
        SAEnum(ControlOwnerType, name="control_owner_type", native_enum=False),
        nullable=False,
    )
    frequency: Mapped[ControlFrequency] = mapped_column(
        SAEnum(ControlFrequency, name="control_frequency", native_enum=False),
        nullable=False,
    )
    automation_level: Mapped[AutomationLevel] = mapped_column(
        SAEnum(AutomationLevel, name="automation_level", native_enum=False),
        nullable=False,
        default=AutomationLevel.MANUAL,
    )

    #: Which PSOE dimensions this control speaks to. A list because a single
    #: control commonly evidences more than one — e.g. a fatigue check is both
    #: Operating (is it done?) and Effective (does it prevent exceedances?).
    psoe_relevance: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)), nullable=False, default=list
    )

    procedure_reference: Mapped[str | None] = mapped_column(String(500))
    change_note: Mapped[str | None] = mapped_column(Text)

    control: Mapped["Control"] = relationship(back_populates="versions")


class ControlRiskLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Association of a control to a risk it mitigates."""

    __tablename__ = "control_risk_links"
    __table_args__ = (
        UniqueConstraint("control_id", "risk_id", name="uq_control_risk_link"),
    )

    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: Whether this control is the main mitigation for the risk or a
    #: supporting one. Used to order the Control Explorer, not to score.
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)

    control: Mapped["Control"] = relationship(back_populates="risk_links")
    risk: Mapped["Risk"] = relationship(back_populates="control_links")
