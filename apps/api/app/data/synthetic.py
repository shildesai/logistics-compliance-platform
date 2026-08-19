"""Static synthetic dashboard data for the Phase 1 application shell.

This is fixture data only — no compliance rule evaluation happens here.
See docs/DECISIONS.md and docs/IMPLEMENTATION_PLAN.md: real control tests,
evidence ingestion and finding generation are out of scope for this shell.
"""

from app.schemas.dashboard import (
    AuditPackDomain,
    CorrectiveAction,
    DomainStatus,
    EvidenceItem,
    Finding,
    PsoeBreakdown,
)

GENERATED_AT = "2026-08-19T00:00:00Z"

_DOMAINS = [
    "Fatigue / Work-Rest",
    "Fitness to Drive",
    "Scheduling & Speed Risk",
    "Vehicle Maintenance & Roadworthiness",
    "Mass & Dimension",
    "Load Restraint",
    "Driver Competency",
    "Incidents & Corrective Actions",
]

_DOMAIN_CONTROL_COUNTS = {
    "Fatigue / Work-Rest": 8,
    "Fitness to Drive": 4,
    "Scheduling & Speed Risk": 6,
    "Vehicle Maintenance & Roadworthiness": 6,
    "Mass & Dimension": 6,
    "Load Restraint": 6,
    "Driver Competency": 5,
    "Incidents & Corrective Actions": 6,
}


def synthetic_domain_statuses() -> list[DomainStatus]:
    open_findings_by_domain = [3, 1, 4, 2, 2, 1, 0, 2]
    psoe_by_domain = [
        (95, 90, 82, 78),
        (100, 95, 91, 88),
        (90, 85, 70, 65),
        (98, 92, 88, 84),
        (100, 96, 90, 89),
        (92, 88, 84, 80),
        (100, 100, 97, 95),
        (96, 90, 86, 83),
    ]
    return [
        DomainStatus(
            domain=domain,
            control_count=_DOMAIN_CONTROL_COUNTS[domain],
            open_findings=open_findings,
            psoe=PsoeBreakdown(
                present=psoe[0], suitable=psoe[1], operating=psoe[2], effective=psoe[3]
            ),
        )
        for domain, open_findings, psoe in zip(
            _DOMAINS, open_findings_by_domain, psoe_by_domain, strict=True
        )
    ]


def synthetic_evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            evidence_id="EVD-10021",
            source_system="EWD",
            entity="Driver D-4471",
            captured_at="2026-08-18T22:14:00Z",
            control_test_id="FAT-001",
            status="processed",
        ),
        EvidenceItem(
            evidence_id="EVD-10022",
            source_system="Fleet Maintenance",
            entity="Vehicle V-2209",
            captured_at="2026-08-18T19:02:00Z",
            control_test_id="MNT-002",
            status="processed",
        ),
        EvidenceItem(
            evidence_id="EVD-10023",
            source_system="TMS",
            entity="Trip T-88213",
            captured_at="2026-08-18T15:47:00Z",
            control_test_id="SCH-001",
            status="processed",
        ),
        EvidenceItem(
            evidence_id="EVD-10024",
            source_system="Weighbridge",
            entity="Load L-5521",
            captured_at="2026-08-18T14:30:00Z",
            control_test_id="MDL-001",
            status="pending_review",
        ),
        EvidenceItem(
            evidence_id="EVD-10025",
            source_system="Driver App",
            entity="Load L-5522",
            captured_at="2026-08-18T11:05:00Z",
            control_test_id="LDR-001",
            status="processed",
        ),
    ]


def synthetic_findings() -> list[Finding]:
    return [
        Finding(
            finding_id="FND-3001",
            control_test_id="FAT-001",
            domain="Fatigue / Work-Rest",
            severity="High",
            status="potential",
            confidence=0.86,
            affected_entity="Driver D-4471",
        ),
        Finding(
            finding_id="FND-3002",
            control_test_id="MNT-002",
            domain="Vehicle Maintenance & Roadworthiness",
            severity="Critical",
            status="confirmed",
            confidence=0.97,
            affected_entity="Vehicle V-2209",
        ),
        Finding(
            finding_id="FND-3003",
            control_test_id="SCH-002",
            domain="Scheduling & Speed Risk",
            severity="High",
            status="potential",
            confidence=0.74,
            affected_entity="Trip T-88213",
        ),
        Finding(
            finding_id="FND-3004",
            control_test_id="DRV-001",
            domain="Driver Competency",
            severity="Critical",
            status="confirmed",
            confidence=0.99,
            affected_entity="Driver D-1187",
        ),
    ]


def synthetic_corrective_actions() -> list[CorrectiveAction]:
    return [
        CorrectiveAction(
            car_id="CAR-9001",
            finding_id="FND-3002",
            owner="Fleet Manager - J. Alvarez",
            due_date="2026-08-22",
            status="in_progress",
        ),
        CorrectiveAction(
            car_id="CAR-9002",
            finding_id="FND-3004",
            owner="Compliance Manager - S. Chen",
            due_date="2026-08-20",
            status="overdue",
        ),
        CorrectiveAction(
            car_id="CAR-9003",
            finding_id="FND-3001",
            owner="Ops Supervisor - R. Patel",
            due_date="2026-08-25",
            status="not_started",
        ),
    ]


def synthetic_audit_pack() -> list[AuditPackDomain]:
    return [
        AuditPackDomain(domain="Fatigue / Work-Rest", population=142, exceptions=6, status="ready"),
        AuditPackDomain(domain="Fitness to Drive", population=98, exceptions=2, status="ready"),
        AuditPackDomain(
            domain="Vehicle Maintenance & Roadworthiness",
            population=211,
            exceptions=9,
            status="ready",
        ),
        AuditPackDomain(domain="Mass & Dimension", population=176, exceptions=4, status="ready"),
        AuditPackDomain(domain="Load Restraint", population=133, exceptions=5, status="in_progress"),
    ]
