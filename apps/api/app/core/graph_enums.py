"""Vocabulary of the Compliance Control Graph.

These are platform concepts with code-level meaning (the test engine dispatches
on `TestType`, the applicability engine reads `PsoeDimension`), so they are
enums rather than reference tables — a tenant cannot invent a new test type and
have anything execute it.
"""

from enum import StrEnum


class LifecycleStatus(StrEnum):
    """Governance state of a versioned regulatory record.

    The progression is DRAFT → IN_REVIEW → APPROVED → ACTIVE, then either
    SUPERSEDED (a newer version took over) or RETIRED (withdrawn with no
    successor). Only ACTIVE versions are used to evaluate compliance; only
    ACTIVE and SUPERSEDED versions are immutable.
    """

    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


#: Statuses meaning "this content was published and governed its effective
#: window" — whether or not it still does.
#:
#: This is the set an as-at query resolves against, and getting it wrong is
#: subtle: a version that has since been SUPERSEDED was still *the* governing
#: rule during its window, so a query for a past date must return it. Matching
#: only ACTIVE would make every historical question return "no rule applied",
#: which is both wrong and the opposite of why effective-dating exists.
PUBLISHED_STATUSES: frozenset[LifecycleStatus] = frozenset(
    {LifecycleStatus.ACTIVE, LifecycleStatus.SUPERSEDED, LifecycleStatus.RETIRED}
)

#: Statuses whose content must never be edited in place. Changing an ACTIVE or
#: SUPERSEDED version would retroactively alter what a past assessment was
#: measured against — see CLAUDE.md ("Never modify a regulatory rule without
#: creating a new version").
#:
#: Coincides with PUBLISHED_STATUSES, and necessarily so: content becomes
#: immutable exactly when it becomes binding on someone. Kept as a separate
#: name because the two express different rules and could diverge.
IMMUTABLE_STATUSES: frozenset[LifecycleStatus] = PUBLISHED_STATUSES

#: Statuses that can still be edited freely, because nothing has been assessed
#: against them yet.
EDITABLE_STATUSES: frozenset[LifecycleStatus] = frozenset(
    {LifecycleStatus.DRAFT, LifecycleStatus.IN_REVIEW, LifecycleStatus.APPROVED}
)


class TestType(StrEnum):
    """How a control test reaches its result.

    DETERMINISTIC is preferred wherever the rule is objectively calculable
    (CLAUDE.md principle 7). AI_ASSISTED output is always a *potential* finding
    requiring human review — it can never be a final determination.
    """

    DETERMINISTIC = "DETERMINISTIC"
    ANALYTICAL = "ANALYTICAL"
    AI_ASSISTED = "AI_ASSISTED"
    MANUAL = "MANUAL"


class PsoeDimension(StrEnum):
    """The assurance question a control speaks to.

    Present    — does the control exist?
    Suitable   — is it appropriate for this operation's risk profile?
    Operating  — is it being performed consistently?
    Effective  — is it actually reducing the risk?
    """

    PRESENT = "PRESENT"
    SUITABLE = "SUITABLE"
    OPERATING = "OPERATING"
    EFFECTIVE = "EFFECTIVE"


class ControlOwnerType(StrEnum):
    """Role archetype accountable for a control.

    A type rather than a named person: the graph is shared reference data, so
    it can only say "a fleet manager owns this", not who that is at a given
    operator.
    """

    COMPLIANCE_MANAGER = "COMPLIANCE_MANAGER"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"
    FLEET_MANAGER = "FLEET_MANAGER"
    SITE_MANAGER = "SITE_MANAGER"
    SCHEDULER = "SCHEDULER"
    EXECUTIVE = "EXECUTIVE"
    SUPPLIER_MANAGER = "SUPPLIER_MANAGER"


class ControlFrequency(StrEnum):
    CONTINUOUS = "CONTINUOUS"
    PER_TRIP = "PER_TRIP"
    PER_SHIFT = "PER_SHIFT"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    EVENT_DRIVEN = "EVENT_DRIVEN"


class AutomationLevel(StrEnum):
    """How much of the control runs without human action."""

    MANUAL = "MANUAL"
    SEMI_AUTOMATED = "SEMI_AUTOMATED"
    AUTOMATED = "AUTOMATED"


class EvidenceSourceType(StrEnum):
    """Kind of system an evidence requirement is satisfied from."""

    TMS = "TMS"
    EWD = "EWD"
    TELEMATICS = "TELEMATICS"
    FLEET_MAINTENANCE = "FLEET_MAINTENANCE"
    HR_LMS = "HR_LMS"
    WMS = "WMS"
    WEIGHBRIDGE = "WEIGHBRIDGE"
    PERMIT_REGISTER = "PERMIT_REGISTER"
    DRIVER_APP = "DRIVER_APP"
    INCIDENT_SYSTEM = "INCIDENT_SYSTEM"
    SUPPLIER_PORTAL = "SUPPLIER_PORTAL"
    DOCUMENT = "DOCUMENT"
    MANUAL_ATTESTATION = "MANUAL_ATTESTATION"


class RiskLikelihood(StrEnum):
    RARE = "RARE"
    UNLIKELY = "UNLIKELY"
    POSSIBLE = "POSSIBLE"
    LIKELY = "LIKELY"
    ALMOST_CERTAIN = "ALMOST_CERTAIN"


class RiskConsequence(StrEnum):
    INSIGNIFICANT = "INSIGNIFICANT"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    SEVERE = "SEVERE"
