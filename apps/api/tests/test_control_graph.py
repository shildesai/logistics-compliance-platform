"""Tests for the Compliance Control Graph: traversal, versioning and API.

These run against a real seeded graph inside the test transaction, so they
exercise the actual relationships and version resolution rather than mocks.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.core.graph_enums import LifecycleStatus, TestType
from app.models import (
    Control,
    ControlTest,
    ControlVersion,
    Obligation,
    Regulation,
    Risk,
)
from app.services import control_graph as graph
from tests.conftest import auth

BEFORE_AMENDMENT = date(2025, 6, 1)
AFTER_AMENDMENT = date(2026, 8, 19)
BEFORE_GRAPH_EXISTS = date(2020, 1, 1)


# --- Structure ------------------------------------------------------------


def test_seeded_graph_has_the_expected_shape(db, control_graph):
    assert db.execute(select(Regulation)).scalars().all()
    assert len(db.execute(select(Obligation)).scalars().all()) == 3
    assert len(db.execute(select(Risk)).scalars().all()) == 3
    assert len(db.execute(select(Control)).scalars().all()) == 2
    assert len(db.execute(select(ControlTest)).scalars().all()) == 5


def test_all_four_test_types_are_represented(db, control_graph):
    """The sample must exercise every branch the engine will dispatch on."""
    from app.models import ControlTestVersion

    types = {
        v.test_type for v in db.execute(select(ControlTestVersion)).scalars().all()
    }
    assert types == set(TestType)


def test_ai_assisted_tests_always_require_human_review(db, control_graph):
    """AI may raise a potential finding but never make a determination."""
    from app.models import ControlTestVersion

    ai_versions = (
        db.execute(
            select(ControlTestVersion).where(
                ControlTestVersion.test_type == TestType.AI_ASSISTED
            )
        )
        .scalars()
        .all()
    )
    assert ai_versions, "sample data should include an AI-assisted test"
    for version in ai_versions:
        assert version.human_review_required is True


def test_rule_configuration_is_structured_data(db, control_graph):
    """Rules are versioned data, never code — that is what allows a threshold
    change to become a new version rather than a deploy."""
    from app.models import ControlTestVersion

    for version in db.execute(select(ControlTestVersion)).scalars().all():
        assert isinstance(version.rule_configuration, dict)
        assert version.rule_configuration.get("kind"), (
            f"{version.name} has no rule kind for the engine to dispatch on"
        )


# --- Version resolution ---------------------------------------------------


def test_control_resolves_to_the_current_version_today(db, control_graph):
    detail = graph.get_control_detail(db, control_graph.fatigue_control.id, as_at=AFTER_AMENDMENT)

    assert detail.version is not None
    assert detail.version.version == 2
    assert detail.version.status is LifecycleStatus.ACTIVE


def test_control_resolves_to_the_superseded_version_for_a_past_date(db, control_graph):
    """The whole point of the model: an assessment dated 2025 must resolve to
    the rule that applied in 2025, not to today's."""
    detail = graph.get_control_detail(
        db, control_graph.fatigue_control.id, as_at=BEFORE_AMENDMENT
    )

    assert detail.version is not None
    assert detail.version.version == 1
    assert detail.version.status is LifecycleStatus.SUPERSEDED


def test_the_two_versions_differ_in_substance(db, control_graph):
    """Guards against a version bump that changed nothing meaningful, which
    would make the history test pass vacuously."""
    old = graph.get_control_detail(
        db, control_graph.fatigue_control.id, as_at=BEFORE_AMENDMENT
    ).version
    new = graph.get_control_detail(
        db, control_graph.fatigue_control.id, as_at=AFTER_AMENDMENT
    ).version

    assert old.frequency != new.frequency
    assert old.automation_level != new.automation_level


def test_control_has_no_version_before_the_graph_existed(db, control_graph):
    detail = graph.get_control_detail(
        db, control_graph.fatigue_control.id, as_at=BEFORE_GRAPH_EXISTS
    )
    assert detail.version is None


# --- Traversal ------------------------------------------------------------


def test_control_detail_includes_risks_and_tests(db, control_graph):
    detail = graph.get_control_detail(db, control_graph.fatigue_control.id)

    assert len(detail.risks) == 2, "fatigue control mitigates risks from two obligations"
    assert len(detail.tests) == 3

    codes = {t.control_test.test_code for t in detail.tests}
    assert codes == {"FAT-001", "FAT-005", "FAT-009"}


def test_control_tests_carry_evidence_requirements(db, control_graph):
    detail = graph.get_control_detail(db, control_graph.fatigue_control.id)
    fat_001 = next(t for t in detail.tests if t.control_test.test_code == "FAT-001")

    assert len(fat_001.evidence_requirements) == 2
    sources = {e.source_type.value for e in fat_001.evidence_requirements}
    assert sources == {"EWD", "TMS"}


def test_control_tests_carry_remediation_templates(db, control_graph):
    detail = graph.get_control_detail(db, control_graph.fatigue_control.id)
    fat_001 = next(t for t in detail.tests if t.control_test.test_code == "FAT-001")

    assert len(fat_001.remediation_templates) == 1
    template = fat_001.remediation_templates[0]
    assert template.requires_closure_evidence is True
    assert template.suggested_steps


def test_missing_control_raises_not_found(db, control_graph):
    import uuid

    with pytest.raises(graph.GraphNotFound):
        graph.get_control_detail(db, uuid.uuid4())


# --- Lineage --------------------------------------------------------------


def test_lineage_traces_the_full_chain_to_the_regulation(db, control_graph):
    lineage = graph.get_control_lineage(db, control_graph.maintenance_control.id)

    assert len(lineage.paths) == 1
    path = lineage.paths[0]
    assert path.regulation.regulation_code == "HVNL"
    assert path.obligation.obligation_code == "OBL-ROADWORTHY"
    assert path.risk.risk_code == "RSK-UNSAFE-VEHICLE"
    assert path.is_primary_control is True


def test_a_shared_control_has_multiple_lineage_paths(db, control_graph):
    """Shared-control architecture: one control satisfies several obligations,
    so lineage must present every route to it rather than an arbitrary one."""
    lineage = graph.get_control_lineage(db, control_graph.fatigue_control.id)

    assert len(lineage.paths) == 2
    obligations = {p.obligation.obligation_code for p in lineage.paths}
    assert obligations == {"OBL-FATIGUE", "OBL-SAFE-SCHEDULING"}


def test_lineage_marks_which_path_is_the_primary_mitigation(db, control_graph):
    lineage = graph.get_control_lineage(db, control_graph.fatigue_control.id)
    primary = [p for p in lineage.paths if p.is_primary_control]

    assert len(primary) == 1
    assert primary[0].obligation.obligation_code == "OBL-FATIGUE"


def test_lineage_includes_applicability_rules(db, control_graph):
    lineage = graph.get_control_lineage(db, control_graph.fatigue_control.id)
    fatigue_path = next(
        p for p in lineage.paths if p.obligation.obligation_code == "OBL-FATIGUE"
    )

    assert len(fatigue_path.applicability_rules) == 1
    rule = fatigue_path.applicability_rules[0]
    # Criteria are data, evaluated server-side.
    assert "jurisdictions" in rule.criteria
    assert "WA" not in rule.criteria["jurisdictions"], "WA is not an HVNL participant"
    assert "NT" not in rule.criteria["jurisdictions"]


def test_lineage_exposes_the_full_version_history(db, control_graph):
    """Lineage that only shows the current rule cannot answer 'what did we
    assess against then?', so history includes superseded versions."""
    lineage = graph.get_control_lineage(db, control_graph.fatigue_control.id)

    assert [v.version for v in lineage.control_version_history] == [1, 2]
    statuses = {v.status for v in lineage.control_version_history}
    assert LifecycleStatus.SUPERSEDED in statuses
    assert LifecycleStatus.ACTIVE in statuses


def test_lineage_includes_test_version_history(db, control_graph):
    lineage = graph.get_control_lineage(db, control_graph.fatigue_control.id)

    assert set(lineage.test_version_history) == {"FAT-001", "FAT-005", "FAT-009"}
    assert all(versions for versions in lineage.test_version_history.values())


# --- Browse ---------------------------------------------------------------


def test_obligations_can_be_filtered_by_cor_role(db, control_graph):
    scheduler_duties = graph.list_obligations(db, cor_role_code="SCHEDULER")
    codes = {o.obligation_code for o in scheduler_duties}

    assert "OBL-SAFE-SCHEDULING" in codes
    # Roadworthiness attaches to operators/employers, not schedulers.
    assert "OBL-ROADWORTHY" not in codes


def test_obligations_can_be_filtered_by_regulation(db, control_graph):
    obligations = graph.list_obligations(db, regulation_id=control_graph.regulation.id)
    assert len(obligations) == 3


def test_controls_can_be_filtered_by_domain(db, control_graph):
    controls = graph.list_controls(db, domain="Fatigue / Work-Rest")
    assert len(controls) == 1
    assert controls[0][0].control_code == "CTL-FAT-001"


def test_regulation_with_no_version_in_force_is_still_listed(db, control_graph):
    """A lapsed regulation is a governance gap to surface, not to hide."""
    listed = graph.list_regulations(db, as_at=BEFORE_GRAPH_EXISTS)

    assert len(listed) == 1
    regulation, version = listed[0]
    assert regulation.regulation_code == "HVNL"
    assert version is None


# --- API ------------------------------------------------------------------


def test_browse_regulations_endpoint(client, two_tenants, control_graph):
    response = client.get(
        "/api/v1/control-graph/regulations",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 200
    body = response.json()
    assert body[0]["regulation"]["regulation_code"] == "HVNL"
    assert body[0]["current_version"]["jurisdiction_codes"]


def test_browse_obligations_endpoint(client, two_tenants, control_graph):
    response = client.get(
        "/api/v1/control-graph/obligations",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_inspect_control_endpoint(client, two_tenants, control_graph):
    response = client.get(
        f"/api/v1/control-graph/controls/{control_graph.fatigue_control.id}",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_version"]["version"] == 2
    assert len(body["tests"]) == 3
    assert len(body["risks"]) == 2


def test_inspect_control_as_at_endpoint(client, two_tenants, control_graph):
    response = client.get(
        f"/api/v1/control-graph/controls/{control_graph.fatigue_control.id}",
        params={"as_at": BEFORE_AMENDMENT.isoformat()},
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 200
    assert response.json()["current_version"]["version"] == 1


def test_inspect_lineage_endpoint(client, two_tenants, control_graph):
    response = client.get(
        f"/api/v1/control-graph/controls/{control_graph.fatigue_control.id}/lineage",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["paths"]) == 2
    assert len(body["control_version_history"]) == 2


def test_control_graph_requires_authentication(client, control_graph):
    assert client.get("/api/v1/control-graph/regulations").status_code == 401


def test_control_graph_requires_an_organisation_context(client, two_tenants, control_graph):
    response = client.get(
        "/api/v1/control-graph/controls",
        headers={"X-User-Id": str(two_tenants.a.admin.id)},
    )
    assert response.status_code == 404


def test_graph_is_shared_reference_data_across_tenants(client, two_tenants, control_graph):
    """The graph is platform-scoped: both tenants legitimately see the same
    regulations. This is not a tenancy leak — it contains no customer data."""
    a = client.get(
        "/api/v1/control-graph/regulations",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    b = client.get(
        "/api/v1/control-graph/regulations",
        headers=auth(two_tenants.b.admin, two_tenants.b.organisation),
    )
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()


def test_read_only_role_can_browse_the_graph(client, two_tenants, control_graph):
    response = client.get(
        "/api/v1/control-graph/controls",
        headers=auth(two_tenants.a.read_only, two_tenants.a.organisation),
    )
    assert response.status_code == 200
