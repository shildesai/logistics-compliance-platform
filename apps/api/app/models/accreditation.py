"""Accreditation records.

IMPORTANT — accreditation is voluntary.

Heavy Vehicle Accreditation is an *optional* scheme for eligible operators. It
is not a legal requirement for operating heavy vehicles, and the great majority
of Chain of Responsibility duties apply regardless of whether an operator is
accredited. Two consequences are binding on anything built on this model:

  1. The absence of an Accreditation row means "not recorded", NOT
     "non-compliant". Never render a missing accreditation as a gap, warning,
     finding, or score reduction.
  2. `NOT_ACCREDITED` is a legitimate, neutral end state — an operator that has
     deliberately chosen not to seek accreditation is in good standing.

See docs/DECISIONS.md and docs/TENANCY.md. A test asserts that no severity or
"compliant" flag is derived from accreditation status.
"""

from datetime import date
from enum import StrEnum

from sqlalchemy import Date
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TenantScoped, TimestampMixin, UUIDPrimaryKeyMixin


class AccreditationScheme(StrEnum):
    HVA = "HVA"  # Heavy Vehicle Accreditation (NHVR)
    NHVAS = "NHVAS"  # National Heavy Vehicle Accreditation Scheme
    WAHVA = "WAHVA"  # Western Australian Heavy Vehicle Accreditation
    OTHER = "OTHER"


class AccreditationModule(StrEnum):
    MASS = "MASS"
    MAINTENANCE = "MAINTENANCE"
    BASIC_FATIGUE = "BASIC_FATIGUE"
    ADVANCED_FATIGUE = "ADVANCED_FATIGUE"
    OTHER = "OTHER"


class AccreditationStatus(StrEnum):
    """Status values.

    NOT_ACCREDITED is neutral and legitimate — accreditation is voluntary.
    It must never be treated as a failure state.
    """

    NOT_ACCREDITED = "NOT_ACCREDITED"
    APPLIED = "APPLIED"
    ACCREDITED = "ACCREDITED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"


#: Statuses that indicate a *previously held* accreditation has lapsed or been
#: acted against. These are meaningful to surface. NOT_ACCREDITED is
#: deliberately absent: never having sought accreditation is not an adverse
#: event and must not be presented as one.
ADVERSE_ACCREDITATION_STATUSES: frozenset[AccreditationStatus] = frozenset(
    {
        AccreditationStatus.SUSPENDED,
        AccreditationStatus.EXPIRED,
    }
)


class Accreditation(Base, UUIDPrimaryKeyMixin, TenantScoped, TimestampMixin):
    __tablename__ = "accreditations"

    scheme: Mapped[AccreditationScheme] = mapped_column(
        SAEnum(AccreditationScheme, name="accreditation_scheme", native_enum=False),
        nullable=False,
    )
    module: Mapped[AccreditationModule] = mapped_column(
        SAEnum(AccreditationModule, name="accreditation_module", native_enum=False),
        nullable=False,
    )
    status: Mapped[AccreditationStatus] = mapped_column(
        SAEnum(AccreditationStatus, name="accreditation_status", native_enum=False),
        nullable=False,
        default=AccreditationStatus.NOT_ACCREDITED,
    )
    accreditation_number: Mapped[str | None] = mapped_column(String(100))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
