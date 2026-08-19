"""Read-side services for the Compliance Control Graph.

Business logic lives here rather than in the API controllers (CLAUDE.md:
"Keep business logic outside API controllers"). Controllers translate HTTP to
these calls and back.

Everything accepts an `as_at` date and resolves versions through
`services.versioning`, so the whole graph can be viewed as it stood on any
date — which is what makes an audit pack reproducible.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.graph_enums import LifecycleStatus
from app.core.tenancy import CrossTenantAccess
from app.models import (
    ApplicabilityRule,
    Control,
    ControlRiskLink,
    ControlTest,
    ControlTestVersion,
    ControlVersion,
    EvidenceRequirement,
    Obligation,
    Regulation,
    RegulationVersion,
    RemediationTemplate,
    Risk,
)
from app.services.versioning import resolve_as_at


class GraphNotFound(CrossTenantAccess):
    """Requested graph node does not exist (404, consistent with tenancy)."""


def _today(as_at: date | None) -> date:
    return as_at or date.today()


def _active(rows, on: date):
    """Filter in-place-versioned rows to those in force on `on`."""
    return [r for r in rows if r.is_in_force_on(on)]


def _latest_per_code(rows, on: date, code_attr: str):
    """Resolve in-place-versioned rows to one row per logical record.

    Rows sharing a code are successive versions of the same thing, so group by
    code and pick the one in force.
    """
    by_code: dict[str, list] = {}
    for row in rows:
        by_code.setdefault(getattr(row, code_attr), []).append(row)
    resolved = []
    for versions in by_code.values():
        found = resolve_as_at(versions, on)
        if found is not None:
            resolved.append(found)
    return resolved


# --- Browse ---------------------------------------------------------------


def list_regulations(db: Session, *, as_at: date | None = None) -> list[tuple[Regulation, RegulationVersion | None]]:
    """Every regulation with the version in force on `as_at`.

    Regulations with no version in force are still returned (paired with None)
    rather than hidden — a regulation whose version lapsed is a governance gap
    the compliance team needs to see, not something to quietly omit.
    """
    on = _today(as_at)
    regulations = (
        db.execute(
            select(Regulation)
            .options(selectinload(Regulation.versions))
            .order_by(Regulation.regulation_code)
        )
        .scalars()
        .all()
    )
    return [(r, resolve_as_at(r.versions, on)) for r in regulations]


def get_regulation(
    db: Session, regulation_id: uuid.UUID, *, as_at: date | None = None
) -> tuple[Regulation, RegulationVersion | None]:
    on = _today(as_at)
    regulation = db.execute(
        select(Regulation)
        .options(selectinload(Regulation.versions))
        .where(Regulation.id == regulation_id)
    ).scalar_one_or_none()
    if regulation is None:
        raise GraphNotFound(f"Regulation {regulation_id} not found")
    return regulation, resolve_as_at(regulation.versions, on)


def list_obligations(
    db: Session,
    *,
    as_at: date | None = None,
    regulation_id: uuid.UUID | None = None,
    cor_role_code: str | None = None,
) -> list[Obligation]:
    on = _today(as_at)
    stmt = select(Obligation)
    if regulation_id is not None:
        stmt = stmt.where(Obligation.regulation_id == regulation_id)
    rows = db.execute(stmt).scalars().all()

    obligations = _latest_per_code(rows, on, "obligation_code")

    if cor_role_code is not None:
        # An obligation with no CoR roles listed is unrestricted by role, so it
        # matches every filter rather than none.
        obligations = [
            o for o in obligations if not o.cor_role_codes or cor_role_code in o.cor_role_codes
        ]

    return sorted(obligations, key=lambda o: o.obligation_code)


def get_obligation(
    db: Session, obligation_id: uuid.UUID, *, as_at: date | None = None
) -> Obligation:
    obligation = db.execute(
        select(Obligation)
        .options(
            selectinload(Obligation.risks),
            selectinload(Obligation.applicability_rules),
            selectinload(Obligation.regulation),
        )
        .where(Obligation.id == obligation_id)
    ).scalar_one_or_none()
    if obligation is None:
        raise GraphNotFound(f"Obligation {obligation_id} not found")
    return obligation


def list_controls(
    db: Session,
    *,
    as_at: date | None = None,
    domain: str | None = None,
) -> list[tuple[Control, ControlVersion | None]]:
    on = _today(as_at)
    stmt = select(Control).options(selectinload(Control.versions))
    if domain is not None:
        stmt = stmt.where(Control.domain == domain)
    controls = db.execute(stmt.order_by(Control.control_code)).scalars().all()
    return [(c, resolve_as_at(c.versions, on)) for c in controls]


def list_control_domains(db: Session) -> list[str]:
    return sorted(
        db.execute(select(Control.domain).distinct()).scalars().all()
    )


# --- Inspect --------------------------------------------------------------


@dataclass
class ControlTestDetail:
    control_test: ControlTest
    version: ControlTestVersion | None
    evidence_requirements: list[EvidenceRequirement] = field(default_factory=list)
    remediation_templates: list[RemediationTemplate] = field(default_factory=list)


@dataclass
class ControlDetail:
    control: Control
    version: ControlVersion | None
    risks: list[Risk] = field(default_factory=list)
    tests: list[ControlTestDetail] = field(default_factory=list)


def get_control_detail(
    db: Session, control_id: uuid.UUID, *, as_at: date | None = None
) -> ControlDetail:
    """A control with its in-force version, mitigated risks and tests."""
    on = _today(as_at)

    control = db.execute(
        select(Control)
        .options(
            selectinload(Control.versions),
            selectinload(Control.risk_links).selectinload(ControlRiskLink.risk),
            selectinload(Control.tests).selectinload(ControlTest.versions),
        )
        .where(Control.id == control_id)
    ).scalar_one_or_none()
    if control is None:
        raise GraphNotFound(f"Control {control_id} not found")

    risks = _active([link.risk for link in control.risk_links], on)

    tests: list[ControlTestDetail] = []
    for test in sorted(control.tests, key=lambda t: t.test_code):
        version = resolve_as_at(test.versions, on)
        detail = ControlTestDetail(control_test=test, version=version)
        if version is not None:
            detail.evidence_requirements = sorted(
                _latest_per_code(version.evidence_requirements, on, "requirement_code"),
                key=lambda e: e.requirement_code,
            )
            detail.remediation_templates = sorted(
                _latest_per_code(version.remediation_templates, on, "template_code"),
                key=lambda t: t.template_code,
            )
        tests.append(detail)

    return ControlDetail(
        control=control,
        version=resolve_as_at(control.versions, on),
        risks=sorted(risks, key=lambda r: r.risk_code),
        tests=tests,
    )


# --- Lineage --------------------------------------------------------------


@dataclass
class LineagePath:
    """One traversal from a regulation down to the control."""

    regulation: Regulation
    regulation_version: RegulationVersion | None
    obligation: Obligation
    applicability_rules: list[ApplicabilityRule]
    risk: Risk
    is_primary_control: bool


@dataclass
class ControlLineage:
    """Why a control exists, and the full version history behind it.

    A control can be reached by more than one path (shared-control
    architecture), so `paths` is a list — that plurality is the point, not an
    edge case.
    """

    control: Control
    current_version: ControlVersion | None
    paths: list[LineagePath] = field(default_factory=list)
    control_version_history: list[ControlVersion] = field(default_factory=list)
    test_version_history: dict[str, list[ControlTestVersion]] = field(default_factory=dict)


def get_control_lineage(
    db: Session, control_id: uuid.UUID, *, as_at: date | None = None
) -> ControlLineage:
    """Trace Regulation → Obligation → Risk → Control, plus version history."""
    on = _today(as_at)

    control = db.execute(
        select(Control)
        .options(
            selectinload(Control.versions),
            selectinload(Control.risk_links)
            .selectinload(ControlRiskLink.risk)
            .selectinload(Risk.obligation)
            .selectinload(Obligation.regulation)
            .selectinload(Regulation.versions),
            selectinload(Control.risk_links)
            .selectinload(ControlRiskLink.risk)
            .selectinload(Risk.obligation)
            .selectinload(Obligation.applicability_rules),
            selectinload(Control.tests).selectinload(ControlTest.versions),
        )
        .where(Control.id == control_id)
    ).scalar_one_or_none()
    if control is None:
        raise GraphNotFound(f"Control {control_id} not found")

    paths: list[LineagePath] = []
    for link in control.risk_links:
        risk = link.risk
        if not risk.is_in_force_on(on):
            continue
        obligation = risk.obligation
        if not obligation.is_in_force_on(on):
            continue
        regulation = obligation.regulation
        paths.append(
            LineagePath(
                regulation=regulation,
                regulation_version=resolve_as_at(regulation.versions, on),
                obligation=obligation,
                applicability_rules=sorted(
                    _latest_per_code(obligation.applicability_rules, on, "rule_code"),
                    key=lambda r: r.rule_code,
                ),
                risk=risk,
                is_primary_control=link.is_primary,
            )
        )

    paths.sort(key=lambda p: (p.regulation.regulation_code, p.obligation.obligation_code))

    return ControlLineage(
        control=control,
        current_version=resolve_as_at(control.versions, on),
        paths=paths,
        # Full history, including superseded versions: lineage that only shows
        # the current rule cannot answer "what did we assess against then?".
        control_version_history=sorted(control.versions, key=lambda v: v.version),
        test_version_history={
            test.test_code: sorted(test.versions, key=lambda v: v.version)
            for test in sorted(control.tests, key=lambda t: t.test_code)
        },
    )


def graph_statistics(db: Session, *, as_at: date | None = None) -> dict[str, int]:
    """Headline counts for the Control Explorer landing view."""
    on = _today(as_at)
    return {
        "regulations": len(db.execute(select(Regulation.id)).scalars().all()),
        "obligations": len(list_obligations(db, as_at=on)),
        "controls": len(db.execute(select(Control.id)).scalars().all()),
        "control_tests": len(db.execute(select(ControlTest.id)).scalars().all()),
        "active_control_versions": len(
            db.execute(
                select(ControlVersion.id).where(
                    ControlVersion.status == LifecycleStatus.ACTIVE
                )
            )
            .scalars()
            .all()
        ),
    }
