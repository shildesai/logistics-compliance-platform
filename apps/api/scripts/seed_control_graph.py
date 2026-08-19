"""Seed a small sample of the Compliance Control Graph.

Deliberately narrow: two complete chains (fatigue and vehicle maintenance)
traced all the way from regulation to evidence requirement, rather than a wide
but shallow import of the whole catalogue. A small complete slice exercises
every relationship and every version state; a wide shallow one exercises none.

What the sample demonstrates:

  * a full Regulation → Obligation → Risk → Control → ControlTest →
    EvidenceRequirement chain, twice;
  * **a superseded version** — CTL-FAT-001 is at version 2 after a 2026
    fatigue-threshold change, with version 1 retained and closed, so lineage
    and as-at queries have real history to resolve against;
  * **a shared control** — CTL-FAT-001 mitigates risks arising from two
    different obligations, which is the shared-control architecture the
    product depends on;
  * all four test types, including a MANUAL test with no automated rule and an
    AI_ASSISTED test that necessarily requires human review.

The content is illustrative sample data for development. It is not a
maintained legal mapping, and the thresholds in it must be reviewed by a
compliance specialist before they are used for any real assessment.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.graph_enums import (  # noqa: E402
    AutomationLevel,
    ControlFrequency,
    ControlOwnerType,
    EvidenceSourceType,
    LifecycleStatus,
    PsoeDimension,
    RiskConsequence,
    RiskLikelihood,
    TestType,
)
from app.db.session import engine  # noqa: E402
from app.models import (  # noqa: E402
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
    RegulatorySource,
    RemediationTemplate,
    Risk,
    User,
)

PRODUCTION_LIKE = {"production", "prod", "staging"}

#: Sample graph dates. The fatigue control changes on this date, giving the
#: as-at queries a real boundary to resolve across.
GRAPH_START = date(2024, 7, 1)
FATIGUE_AMENDMENT = date(2026, 2, 1)


def _governance(db: Session) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Reviewer/approver for seeded content.

    Uses the seeded platform administrator when present. Versions cannot be
    ACTIVE without both recorded, so this is not decorative.
    """
    user = db.execute(
        select(User).where(User.is_platform_admin.is_(True)).order_by(User.email)
    ).scalars().first()
    return (user.id if user else None, user.id if user else None)


def seed(db: Session) -> dict[str, int]:
    if db.execute(select(Regulation.id)).scalars().first() is not None:
        return {"skipped": 1}

    reviewed_by, approved_by = _governance(db)
    if reviewed_by is None:
        raise SystemExit(
            "No platform administrator found. Run scripts/seed_dev_data.py first — "
            "an ACTIVE version requires a recorded reviewer and approver."
        )

    gov = {
        "reviewed_by_id": reviewed_by,
        "approved_by_id": approved_by,
        "status": LifecycleStatus.ACTIVE,
    }
    HVNL_STATES = ["NSW", "VIC", "QLD", "SA", "TAS", "ACT"]

    # --- Sources ---------------------------------------------------------
    hvnl_source = RegulatorySource(
        source_code="NHVR-HVNL",
        name="Heavy Vehicle National Law and Regulations",
        publisher="National Heavy Vehicle Regulator",
        url="https://www.nhvr.gov.au/law-policies/heavy-vehicle-national-law-and-regulations",
        document_type="Legislation",
        retrieved_on=date(2026, 8, 18),
    )
    fatigue_source = RegulatorySource(
        source_code="NHVR-FATIGUE",
        name="NHVR Fatigue Management guidance",
        publisher="National Heavy Vehicle Regulator",
        url="https://www.nhvr.gov.au/safety-accreditation-compliance/fatigue-management",
        document_type="Guidance",
        retrieved_on=date(2026, 8, 18),
    )
    db.add_all([hvnl_source, fatigue_source])
    db.flush()

    # --- Regulation ------------------------------------------------------
    hvnl = Regulation(
        regulation_code="HVNL",
        name="Heavy Vehicle National Law",
        short_name="HVNL",
        regulator="National Heavy Vehicle Regulator",
    )
    db.add(hvnl)
    db.flush()

    db.add(
        RegulationVersion(
            regulation_id=hvnl.id,
            regulatory_source_id=hvnl_source.id,
            version=1,
            effective_from=GRAPH_START,
            effective_to=None,
            source_reference="Heavy Vehicle National Law (consolidated)",
            title="Heavy Vehicle National Law",
            summary=(
                "National law governing heavy vehicle operations, including primary "
                "duty and Chain of Responsibility obligations."
            ),
            jurisdiction_codes=HVNL_STATES,
            **gov,
        )
    )

    # --- Obligations -----------------------------------------------------
    fatigue_obligation = Obligation(
        obligation_code="OBL-FATIGUE",
        regulation_id=hvnl.id,
        version=1,
        effective_from=GRAPH_START,
        source_reference="HVNL Ch 6 — Vehicle operations: fatigue",
        name="Manage heavy vehicle driver fatigue",
        description=(
            "Ensure drivers of fatigue-regulated heavy vehicles do not drive while "
            "impaired by fatigue, and that work and rest arrangements comply with the "
            "applicable work/rest limits."
        ),
        cor_role_codes=["OPERATOR", "EMPLOYER", "SCHEDULER", "PRIME_CONTRACTOR"],
        **gov,
    )
    scheduling_obligation = Obligation(
        obligation_code="OBL-SAFE-SCHEDULING",
        regulation_id=hvnl.id,
        version=1,
        effective_from=GRAPH_START,
        source_reference="HVNL s 26C — Primary duty",
        name="Do not create unreasonable transport safety risk through scheduling",
        description=(
            "Transport arrangements, including delivery timeframes and schedules, must "
            "not require or encourage a driver to exceed work/rest limits or speed limits."
        ),
        cor_role_codes=["SCHEDULER", "CONSIGNOR", "CONSIGNEE", "OPERATOR"],
        **gov,
    )
    roadworthiness_obligation = Obligation(
        obligation_code="OBL-ROADWORTHY",
        regulation_id=hvnl.id,
        version=1,
        effective_from=GRAPH_START,
        source_reference="HVNL Ch 3 — Vehicle operations: standards and safety",
        name="Operate roadworthy heavy vehicles",
        description=(
            "Heavy vehicles used on a road must meet applicable vehicle safety and "
            "roadworthiness standards and be maintained in a safe condition."
        ),
        cor_role_codes=["OPERATOR", "EMPLOYER"],
        **gov,
    )
    db.add_all([fatigue_obligation, scheduling_obligation, roadworthiness_obligation])
    db.flush()

    # --- Applicability rules --------------------------------------------
    db.add_all(
        [
            ApplicabilityRule(
                rule_code="APP-FATIGUE-HVNL",
                obligation_id=fatigue_obligation.id,
                version=1,
                effective_from=GRAPH_START,
                source_reference="HVNL Ch 6 applicability",
                name="Fatigue-regulated heavy vehicles in HVNL jurisdictions",
                description=(
                    "Applies to operators of fatigue-regulated heavy vehicles in "
                    "participating HVNL jurisdictions. WA and NT operate separate "
                    "legislation and are excluded."
                ),
                criteria={
                    "jurisdictions": HVNL_STATES,
                    "cor_roles": ["OPERATOR", "EMPLOYER", "SCHEDULER", "PRIME_CONTRACTOR"],
                    "vehicle_types": ["FATIGUE_REGULATED_HEAVY_VEHICLE"],
                },
                **gov,
            ),
            ApplicabilityRule(
                rule_code="APP-SCHEDULING-COR",
                obligation_id=scheduling_obligation.id,
                version=1,
                effective_from=GRAPH_START,
                source_reference="HVNL s 26C",
                name="Parties who influence transport scheduling",
                description=(
                    "Applies to any party who influences or controls scheduling, "
                    "including consignors and consignees who do not own vehicles."
                ),
                criteria={
                    "jurisdictions": HVNL_STATES,
                    "cor_roles": ["SCHEDULER", "CONSIGNOR", "CONSIGNEE", "OPERATOR"],
                },
                **gov,
            ),
            ApplicabilityRule(
                rule_code="APP-ROADWORTHY",
                obligation_id=roadworthiness_obligation.id,
                version=1,
                effective_from=GRAPH_START,
                source_reference="HVNL Ch 3 applicability",
                name="Operators of heavy vehicles",
                criteria={
                    "jurisdictions": HVNL_STATES,
                    "cor_roles": ["OPERATOR", "EMPLOYER"],
                },
                **gov,
            ),
        ]
    )

    # --- Risks -----------------------------------------------------------
    fatigue_risk = Risk(
        risk_code="RSK-FATIGUE-EXCEED",
        obligation_id=fatigue_obligation.id,
        version=1,
        effective_from=GRAPH_START,
        name="Driver operates beyond work/rest limits",
        description=(
            "A driver works past the applicable limit or without required rest, "
            "increasing the likelihood of a fatigue-related collision."
        ),
        inherent_likelihood=RiskLikelihood.POSSIBLE,
        inherent_consequence=RiskConsequence.SEVERE,
        **gov,
    )
    schedule_fatigue_risk = Risk(
        risk_code="RSK-SCHEDULE-PRESSURE",
        obligation_id=scheduling_obligation.id,
        version=1,
        effective_from=GRAPH_START,
        name="Schedule pressure induces fatigue or speeding",
        description=(
            "Delivery windows leave insufficient time for the journey, pressuring "
            "drivers to skip rest or exceed speed limits."
        ),
        inherent_likelihood=RiskLikelihood.LIKELY,
        inherent_consequence=RiskConsequence.MAJOR,
        **gov,
    )
    defect_risk = Risk(
        risk_code="RSK-UNSAFE-VEHICLE",
        obligation_id=roadworthiness_obligation.id,
        version=1,
        effective_from=GRAPH_START,
        name="Vehicle dispatched with an unrepaired safety defect",
        description=(
            "A vehicle with a known safety-critical defect is assigned to a trip "
            "before the defect is rectified and released to service."
        ),
        inherent_likelihood=RiskLikelihood.POSSIBLE,
        inherent_consequence=RiskConsequence.SEVERE,
        **gov,
    )
    db.add_all([fatigue_risk, schedule_fatigue_risk, defect_risk])
    db.flush()

    # --- Controls --------------------------------------------------------
    fatigue_control = Control(control_code="CTL-FAT-001", domain="Fatigue / Work-Rest")
    maintenance_control = Control(
        control_code="CTL-MNT-001", domain="Vehicle Maintenance & Roadworthiness"
    )
    db.add_all([fatigue_control, maintenance_control])
    db.flush()

    # Version 1: superseded by the 2026 amendment. Retained, not deleted —
    # an assessment made in 2025 must still resolve to this version.
    db.add(
        ControlVersion(
            control_id=fatigue_control.id,
            version=1,
            effective_from=GRAPH_START,
            effective_to=FATIGUE_AMENDMENT,
            status=LifecycleStatus.SUPERSEDED,
            reviewed_by_id=reviewed_by,
            approved_by_id=approved_by,
            source_reference="HVNL Ch 6",
            name="Fatigue monitoring and intervention",
            objective=(
                "Detect and intervene where driver work and rest patterns approach or "
                "breach applicable limits."
            ),
            owner_type=ControlOwnerType.COMPLIANCE_MANAGER,
            frequency=ControlFrequency.DAILY,
            automation_level=AutomationLevel.SEMI_AUTOMATED,
            psoe_relevance=[PsoeDimension.OPERATING, PsoeDimension.EFFECTIVE],
            change_note="Initial version.",
        )
    )
    db.add(
        ControlVersion(
            control_id=fatigue_control.id,
            version=2,
            effective_from=FATIGUE_AMENDMENT,
            effective_to=None,
            source_reference="HVNL Ch 6 (2026 amendment)",
            name="Fatigue monitoring and intervention",
            objective=(
                "Continuously monitor driver work and rest against the effective-dated "
                "fatigue rule pack, and intervene before a limit is breached."
            ),
            owner_type=ControlOwnerType.COMPLIANCE_MANAGER,
            frequency=ControlFrequency.CONTINUOUS,
            automation_level=AutomationLevel.AUTOMATED,
            psoe_relevance=[
                PsoeDimension.SUITABLE,
                PsoeDimension.OPERATING,
                PsoeDimension.EFFECTIVE,
            ],
            change_note=(
                "Moved from daily review to continuous monitoring following the 2026 "
                "fatigue threshold change; automation level raised."
            ),
            **gov,
        )
    )
    db.add(
        ControlVersion(
            control_id=maintenance_control.id,
            version=1,
            effective_from=GRAPH_START,
            source_reference="HVNL Ch 3",
            name="Maintenance, defect and release-to-service",
            objective=(
                "Ensure vehicles with open safety defects are not dispatched, and that "
                "release to service follows recorded rectification."
            ),
            owner_type=ControlOwnerType.FLEET_MANAGER,
            frequency=ControlFrequency.PER_TRIP,
            automation_level=AutomationLevel.SEMI_AUTOMATED,
            psoe_relevance=[PsoeDimension.OPERATING, PsoeDimension.EFFECTIVE],
            **gov,
        )
    )

    # The fatigue control mitigates risks from *two* obligations — the shared
    # control architecture, and why lineage returns a list of paths.
    db.add_all(
        [
            ControlRiskLink(
                control_id=fatigue_control.id, risk_id=fatigue_risk.id, is_primary=True
            ),
            ControlRiskLink(
                control_id=fatigue_control.id,
                risk_id=schedule_fatigue_risk.id,
                is_primary=False,
            ),
            ControlRiskLink(
                control_id=maintenance_control.id, risk_id=defect_risk.id, is_primary=True
            ),
        ]
    )
    db.flush()

    # --- Control tests ---------------------------------------------------
    def add_test(
        control: Control,
        test_code: str,
        *,
        name: str,
        logic: str,
        test_type: TestType,
        rule_configuration: dict,
        severity_configuration: dict,
        human_review_required: bool,
        psoe_impact: list[str],
        effective_from: date = GRAPH_START,
    ) -> ControlTestVersion:
        test = ControlTest(test_code=test_code, control_id=control.id)
        db.add(test)
        db.flush()
        version = ControlTestVersion(
            control_test_id=test.id,
            version=1,
            effective_from=effective_from,
            source_reference="Sample control-test catalogue",
            name=name,
            test_logic_description=logic,
            test_type=test_type,
            rule_configuration=rule_configuration,
            severity_configuration=severity_configuration,
            human_review_required=human_review_required,
            psoe_impact=psoe_impact,
            **gov,
        )
        db.add(version)
        db.flush()
        return version

    fat_001 = add_test(
        fatigue_control,
        "FAT-001",
        name="Work-time threshold exception",
        logic=(
            "Calculate actual work time in the rolling window and compare against the "
            "limit in the effective-dated fatigue rule pack."
        ),
        test_type=TestType.DETERMINISTIC,
        rule_configuration={
            "kind": "threshold_exceeded",
            "metric": "work_time_minutes_in_window",
            "window_hours": 24,
            "limit_minutes": 720,
            "comparison": "gt",
            "rule_pack": "HVNL_STANDARD_HOURS",
        },
        severity_configuration={
            "default": "HIGH",
            "escalations": [
                {"when": {"exceedance_minutes_gte": 60}, "severity": "CRITICAL"}
            ],
        },
        human_review_required=True,
        psoe_impact=[PsoeDimension.OPERATING, PsoeDimension.EFFECTIVE],
    )

    fat_005 = add_test(
        fatigue_control,
        "FAT-005",
        name="Repeat fatigue exceptions",
        logic="Cluster repeated fatigue exceptions by driver, route, scheduler or customer.",
        test_type=TestType.ANALYTICAL,
        rule_configuration={
            "kind": "recurrence_cluster",
            "event": "fatigue_exception",
            "window_days": 30,
            "min_occurrences": 3,
            "group_by": ["driver_id", "route_id", "customer_id"],
        },
        severity_configuration={"default": "HIGH"},
        human_review_required=True,
        psoe_impact=[PsoeDimension.EFFECTIVE],
    )

    fat_009 = add_test(
        fatigue_control,
        "FAT-009",
        name="Fatigue management policy review",
        logic=(
            "A responsible person confirms the documented fatigue policy has been "
            "reviewed within the required period. No automated data source exists."
        ),
        test_type=TestType.MANUAL,
        rule_configuration={
            "kind": "manual_attestation",
            "review_period_months": 12,
            "attestation_role": "COMPLIANCE_MANAGER",
        },
        severity_configuration={"default": "MEDIUM"},
        human_review_required=True,
        psoe_impact=[PsoeDimension.PRESENT, PsoeDimension.SUITABLE],
    )

    mnt_002 = add_test(
        maintenance_control,
        "MNT-002",
        name="Open safety defect at dispatch",
        logic="Vehicle assigned to a trip while a critical defect remains open.",
        test_type=TestType.DETERMINISTIC,
        rule_configuration={
            "kind": "state_conflict",
            "left": {"entity": "defect", "field": "status", "equals": "OPEN"},
            "right": {"entity": "trip", "field": "dispatch_time", "exists": True},
            "severity_field": "defect.severity",
            "qualifying_severities": ["CRITICAL", "MAJOR"],
        },
        severity_configuration={"default": "CRITICAL"},
        human_review_required=True,
        psoe_impact=[PsoeDimension.OPERATING, PsoeDimension.EFFECTIVE],
    )

    mnt_007 = add_test(
        maintenance_control,
        "MNT-007",
        name="Defect photo does not evidence rectification",
        logic=(
            "Image evidence attached to a defect closure does not show the repair "
            "described. Produces a potential finding for human confirmation only."
        ),
        test_type=TestType.AI_ASSISTED,
        rule_configuration={
            "kind": "image_consistency",
            "subject": "defect_closure_photo",
            "compare_against": "defect.description",
            "min_confidence": 0.7,
        },
        severity_configuration={"default": "MEDIUM"},
        # AI output is never a final determination — always human-reviewed.
        human_review_required=True,
        psoe_impact=[PsoeDimension.OPERATING],
    )

    # --- Evidence requirements ------------------------------------------
    db.add_all(
        [
            EvidenceRequirement(
                requirement_code="EVR-FAT-001-EWD",
                control_test_version_id=fat_001.id,
                version=1,
                effective_from=GRAPH_START,
                name="Electronic work diary records",
                description="Work and rest records covering the assessed window.",
                source_type=EvidenceSourceType.EWD,
                required_fields=[
                    "driver_id",
                    "work_start",
                    "work_end",
                    "rest_period",
                    "record_timestamp",
                ],
                is_mandatory=True,
                max_age_days=1,
                **gov,
            ),
            EvidenceRequirement(
                requirement_code="EVR-FAT-001-TMS",
                control_test_version_id=fat_001.id,
                version=1,
                effective_from=GRAPH_START,
                name="Trip and roster schedule",
                description="Planned work used to detect assignments that would breach limits.",
                source_type=EvidenceSourceType.TMS,
                required_fields=["driver_id", "trip_id", "schedule_start", "schedule_end"],
                is_mandatory=True,
                max_age_days=7,
                **gov,
            ),
            EvidenceRequirement(
                requirement_code="EVR-FAT-005-EVENTS",
                control_test_version_id=fat_005.id,
                version=1,
                effective_from=GRAPH_START,
                name="Historical fatigue exception events",
                source_type=EvidenceSourceType.EWD,
                required_fields=["driver_id", "exception_type", "occurred_at", "route_id"],
                is_mandatory=True,
                max_age_days=90,
                **gov,
            ),
            EvidenceRequirement(
                requirement_code="EVR-FAT-009-POLICY",
                control_test_version_id=fat_009.id,
                version=1,
                effective_from=GRAPH_START,
                name="Fatigue policy review attestation",
                source_type=EvidenceSourceType.MANUAL_ATTESTATION,
                required_fields=["document_id", "reviewed_on", "reviewer"],
                is_mandatory=True,
                max_age_days=365,
                **gov,
            ),
            EvidenceRequirement(
                requirement_code="EVR-MNT-002-DEFECT",
                control_test_version_id=mnt_002.id,
                version=1,
                effective_from=GRAPH_START,
                name="Vehicle defect register",
                source_type=EvidenceSourceType.FLEET_MAINTENANCE,
                required_fields=[
                    "vehicle_id",
                    "defect_id",
                    "defect_severity",
                    "status",
                    "raised_at",
                ],
                is_mandatory=True,
                max_age_days=1,
                **gov,
            ),
            EvidenceRequirement(
                requirement_code="EVR-MNT-002-DISPATCH",
                control_test_version_id=mnt_002.id,
                version=1,
                effective_from=GRAPH_START,
                name="Trip dispatch record",
                source_type=EvidenceSourceType.TMS,
                required_fields=["trip_id", "vehicle_id", "dispatch_time"],
                is_mandatory=True,
                max_age_days=1,
                **gov,
            ),
            EvidenceRequirement(
                requirement_code="EVR-MNT-007-PHOTO",
                control_test_version_id=mnt_007.id,
                version=1,
                effective_from=GRAPH_START,
                name="Defect closure photograph",
                source_type=EvidenceSourceType.DRIVER_APP,
                required_fields=["defect_id", "photo_id", "captured_at"],
                # Optional: absence means the test cannot run, which is
                # reported as not-assessable rather than as a pass.
                is_mandatory=False,
                **gov,
            ),
        ]
    )

    # --- Remediation templates ------------------------------------------
    db.add_all(
        [
            RemediationTemplate(
                template_code="REM-FAT-001",
                control_test_version_id=fat_001.id,
                version=1,
                effective_from=GRAPH_START,
                title="Investigate work-time exceedance",
                description=(
                    "Establish why the limit was exceeded and correct the scheduling or "
                    "rostering practice that allowed it."
                ),
                suggested_steps=[
                    "Interview the driver and the scheduler responsible for the trip.",
                    "Review the roster and trip plan that produced the assignment.",
                    "Adjust the roster or delivery window where the plan was infeasible.",
                    "Record manager sign-off of the corrective action.",
                    "Monitor the driver and route for recurrence over 30 days.",
                ],
                default_owner_type=ControlOwnerType.COMPLIANCE_MANAGER,
                default_due_days=7,
                requires_closure_evidence=True,
                requires_effectiveness_check=True,
                **gov,
            ),
            RemediationTemplate(
                template_code="REM-MNT-002",
                control_test_version_id=mnt_002.id,
                version=1,
                effective_from=GRAPH_START,
                title="Ground vehicle and rectify defect",
                description=(
                    "Remove the vehicle from service until the defect is rectified and "
                    "release to service is recorded."
                ),
                suggested_steps=[
                    "Ground the vehicle and reassign the affected trip.",
                    "Complete the repair and record the work order.",
                    "Carry out and record the release-to-service inspection.",
                    "Review why dispatch was possible with the defect open.",
                ],
                default_owner_type=ControlOwnerType.FLEET_MANAGER,
                default_due_days=3,
                requires_closure_evidence=True,
                requires_effectiveness_check=True,
                **gov,
            ),
        ]
    )

    db.flush()
    return {
        "regulatory_sources": 2,
        "regulations": 1,
        "regulation_versions": 1,
        "obligations": 3,
        "applicability_rules": 3,
        "risks": 3,
        "controls": 2,
        "control_versions": 3,
        "control_tests": 5,
        "control_test_versions": 5,
        "evidence_requirements": 7,
        "remediation_templates": 2,
    }


def main() -> None:
    settings = get_settings()
    if settings.environment.lower() in PRODUCTION_LIKE:
        raise SystemExit(
            f"Refusing to seed sample graph data in environment='{settings.environment}'."
        )

    with Session(engine) as db:
        counts = seed(db)
        db.commit()

    if counts.get("skipped"):
        print("Control graph already seeded; nothing to do.")
        return

    print("Seeded sample Compliance Control Graph:\n")
    for name, count in counts.items():
        print(f"  {count:>3}  {name.replace('_', ' ')}")
    print(
        "\nSample data for development only — thresholds are illustrative and require "
        "compliance review before any real use."
    )


if __name__ == "__main__":
    main()
