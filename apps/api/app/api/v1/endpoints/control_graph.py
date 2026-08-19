"""Compliance Control Graph browse and inspect endpoints.

The graph is platform-scoped reference data (see app/models/__init__.py), so
these routes return the same content for every tenant. They still require an
authenticated tenant context: the Control Explorer is a product surface, not a
public catalogue, and requiring `ORG_READ` keeps the authorisation model
uniform across the API.

Controllers here only translate HTTP; the traversal and version resolution
live in app/services/control_graph.py.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentTenant, DbSession
from app.core.roles import Permission
from app.schemas.control_graph import (
    ControlDetailOut,
    ControlLineageOut,
    ControlListItem,
    ControlTestDetailOut,
    GraphStatisticsOut,
    ObligationDetailOut,
    ObligationOut,
    RegulationListItem,
    RegulationVersionOut,
)
from app.services import control_graph as graph

router = APIRouter(prefix="/control-graph", tags=["control-graph"])

AsAt = Query(
    None,
    description=(
        "View the graph as it stood on this date (ISO 8601). Defaults to today. "
        "Use it to reproduce an assessment against the rules that applied at the time."
    ),
)


@router.get("/statistics", response_model=GraphStatisticsOut)
def get_statistics(db: DbSession, context: CurrentTenant, as_at: date | None = AsAt):
    context.require(Permission.ORG_READ)
    return graph.graph_statistics(db, as_at=as_at)


# --- Regulations ----------------------------------------------------------


@router.get("/regulations", response_model=list[RegulationListItem])
def browse_regulations(db: DbSession, context: CurrentTenant, as_at: date | None = AsAt):
    context.require(Permission.ORG_READ)
    return [
        RegulationListItem(regulation=regulation, current_version=version)
        for regulation, version in graph.list_regulations(db, as_at=as_at)
    ]


@router.get("/regulations/{regulation_id}", response_model=RegulationListItem)
def inspect_regulation(
    db: DbSession,
    context: CurrentTenant,
    regulation_id: uuid.UUID,
    as_at: date | None = AsAt,
):
    context.require(Permission.ORG_READ)
    regulation, version = graph.get_regulation(db, regulation_id, as_at=as_at)
    return RegulationListItem(regulation=regulation, current_version=version)


@router.get(
    "/regulations/{regulation_id}/versions", response_model=list[RegulationVersionOut]
)
def list_regulation_versions(
    db: DbSession, context: CurrentTenant, regulation_id: uuid.UUID
):
    """Full version history, including superseded versions."""
    context.require(Permission.ORG_READ)
    regulation, _ = graph.get_regulation(db, regulation_id)
    return sorted(regulation.versions, key=lambda v: v.version)


# --- Obligations ----------------------------------------------------------


@router.get("/obligations", response_model=list[ObligationOut])
def browse_obligations(
    db: DbSession,
    context: CurrentTenant,
    as_at: date | None = AsAt,
    regulation_id: uuid.UUID | None = Query(None),
    cor_role_code: str | None = Query(
        None, description="Filter to duties attaching to this CoR party type."
    ),
):
    context.require(Permission.ORG_READ)
    return graph.list_obligations(
        db, as_at=as_at, regulation_id=regulation_id, cor_role_code=cor_role_code
    )


@router.get("/obligations/{obligation_id}", response_model=ObligationDetailOut)
def inspect_obligation(
    db: DbSession,
    context: CurrentTenant,
    obligation_id: uuid.UUID,
    as_at: date | None = AsAt,
):
    context.require(Permission.ORG_READ)
    return graph.get_obligation(db, obligation_id, as_at=as_at)


# --- Controls -------------------------------------------------------------


@router.get("/controls", response_model=list[ControlListItem])
def browse_controls(
    db: DbSession,
    context: CurrentTenant,
    as_at: date | None = AsAt,
    domain: str | None = Query(None),
):
    context.require(Permission.ORG_READ)
    return [
        ControlListItem(control=control, current_version=version)
        for control, version in graph.list_controls(db, as_at=as_at, domain=domain)
    ]


@router.get("/control-domains", response_model=list[str])
def list_control_domains(db: DbSession, context: CurrentTenant):
    context.require(Permission.ORG_READ)
    return graph.list_control_domains(db)


@router.get("/controls/{control_id}", response_model=ControlDetailOut)
def inspect_control(
    db: DbSession,
    context: CurrentTenant,
    control_id: uuid.UUID,
    as_at: date | None = AsAt,
):
    """A control with its in-force version, the risks it mitigates, and its
    tests with their evidence requirements and remediation templates."""
    context.require(Permission.ORG_READ)
    detail = graph.get_control_detail(db, control_id, as_at=as_at)
    return ControlDetailOut(
        control=detail.control,
        current_version=detail.version,
        risks=detail.risks,
        tests=[
            ControlTestDetailOut(
                control_test=t.control_test,
                current_version=t.version,
                evidence_requirements=t.evidence_requirements,
                remediation_templates=t.remediation_templates,
            )
            for t in detail.tests
        ],
    )


@router.get("/controls/{control_id}/lineage", response_model=ControlLineageOut)
def inspect_control_lineage(
    db: DbSession,
    context: CurrentTenant,
    control_id: uuid.UUID,
    as_at: date | None = AsAt,
):
    """Why this control exists: every Regulation → Obligation → Risk path that
    reaches it, plus the full version history of the control and its tests."""
    context.require(Permission.ORG_READ)
    lineage = graph.get_control_lineage(db, control_id, as_at=as_at)
    return ControlLineageOut(
        control=lineage.control,
        current_version=lineage.current_version,
        paths=[
            {
                "regulation": p.regulation,
                "regulation_version": p.regulation_version,
                "obligation": p.obligation,
                "applicability_rules": p.applicability_rules,
                "risk": p.risk,
                "is_primary_control": p.is_primary_control,
            }
            for p in lineage.paths
        ],
        control_version_history=lineage.control_version_history,
        test_version_history=lineage.test_version_history,
    )
