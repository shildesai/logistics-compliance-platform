"""Static synthetic dashboard data for the Phase 1 application shell.

This is fixture data only — no compliance rule evaluation happens here.
See docs/DECISIONS.md and docs/IMPLEMENTATION_PLAN.md: real control tests,
evidence ingestion and finding generation are out of scope for this shell.

`_FINDINGS` is the single source of truth for finding counts: the per-domain
`open_findings` shown on the Assurance Overview is derived from it, so the
overview and the Findings inbox can never disagree.
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

OPEN_FINDING_STATUSES = frozenset({"potential", "confirmed"})

# Control-test counts per domain, matching the P1 catalogue
# (docs/DECISIONS.md §1.1: 47 P1 tests across these 8 domains).
_DOMAIN_CONTROL_COUNTS: dict[str, int] = {
    "Fatigue / Work-Rest": 8,
    "Fitness to Drive": 4,
    "Scheduling & Speed Risk": 6,
    "Vehicle Maintenance & Roadworthiness": 6,
    "Mass & Dimension": 6,
    "Load Restraint": 6,
    "Driver Competency": 5,
    "Incidents & Corrective Actions": 6,
}

_DOMAIN_PSOE: dict[str, tuple[int, int, int, int]] = {
    "Fatigue / Work-Rest": (95, 90, 82, 78),
    "Fitness to Drive": (100, 95, 91, 88),
    "Scheduling & Speed Risk": (90, 85, 70, 65),
    "Vehicle Maintenance & Roadworthiness": (98, 92, 88, 84),
    "Mass & Dimension": (100, 96, 90, 89),
    "Load Restraint": (92, 88, 84, 80),
    "Driver Competency": (100, 100, 97, 95),
    "Incidents & Corrective Actions": (96, 90, 86, 83),
}

_FINDINGS: list[Finding] = [
    # Fatigue / Work-Rest
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
        control_test_id="FAT-002",
        domain="Fatigue / Work-Rest",
        severity="High",
        status="potential",
        confidence=0.81,
        affected_entity="Driver D-2290",
    ),
    Finding(
        finding_id="FND-3003",
        control_test_id="FAT-005",
        domain="Fatigue / Work-Rest",
        severity="Medium",
        status="confirmed",
        confidence=0.78,
        affected_entity="Route R-118",
    ),
    # Fitness to Drive
    Finding(
        finding_id="FND-3004",
        control_test_id="FIT-001",
        domain="Fitness to Drive",
        severity="Critical",
        status="confirmed",
        confidence=0.95,
        affected_entity="Driver D-1187",
    ),
    # Scheduling & Speed Risk
    Finding(
        finding_id="FND-3005",
        control_test_id="SCH-001",
        domain="Scheduling & Speed Risk",
        severity="High",
        status="potential",
        confidence=0.74,
        affected_entity="Trip T-88213",
    ),
    Finding(
        finding_id="FND-3006",
        control_test_id="SCH-002",
        domain="Scheduling & Speed Risk",
        severity="High",
        status="potential",
        confidence=0.69,
        affected_entity="Trip T-88240",
    ),
    Finding(
        finding_id="FND-3007",
        control_test_id="SCH-003",
        domain="Scheduling & Speed Risk",
        severity="Medium",
        status="potential",
        confidence=0.72,
        affected_entity="Trip T-88251",
    ),
    Finding(
        finding_id="FND-3008",
        control_test_id="SCH-005",
        domain="Scheduling & Speed Risk",
        severity="Medium",
        status="confirmed",
        confidence=0.83,
        affected_entity="Site S-042",
    ),
    # Vehicle Maintenance & Roadworthiness
    Finding(
        finding_id="FND-3009",
        control_test_id="MNT-002",
        domain="Vehicle Maintenance & Roadworthiness",
        severity="Critical",
        status="confirmed",
        confidence=0.97,
        affected_entity="Vehicle V-2209",
    ),
    Finding(
        finding_id="FND-3010",
        control_test_id="MNT-001",
        domain="Vehicle Maintenance & Roadworthiness",
        severity="High",
        status="potential",
        confidence=0.88,
        affected_entity="Vehicle V-2317",
    ),
    # Mass & Dimension
    Finding(
        finding_id="FND-3011",
        control_test_id="MDL-001",
        domain="Mass & Dimension",
        severity="High",
        status="potential",
        confidence=0.91,
        affected_entity="Load L-5521",
    ),
    Finding(
        finding_id="FND-3012",
        control_test_id="MDL-003",
        domain="Mass & Dimension",
        severity="Medium",
        status="potential",
        confidence=0.66,
        affected_entity="Load L-5530",
    ),
    # Load Restraint
    Finding(
        finding_id="FND-3013",
        control_test_id="LDR-004",
        domain="Load Restraint",
        severity="High",
        status="potential",
        confidence=0.79,
        affected_entity="Load L-5522",
    ),
    # Incidents & Corrective Actions
    Finding(
        finding_id="FND-3014",
        control_test_id="CAR-002",
        domain="Incidents & Corrective Actions",
        severity="Medium",
        status="potential",
        confidence=0.70,
        affected_entity="CAR-9002",
    ),
    Finding(
        finding_id="FND-3015",
        control_test_id="CAR-005",
        domain="Incidents & Corrective Actions",
        severity="High",
        status="confirmed",
        confidence=0.84,
        affected_entity="Incident I-7781",
    ),
    # Driver Competency deliberately has no open findings, so the dashboard
    # shows at least one fully clean domain.
]

_EVIDENCE: list[EvidenceItem] = [
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
        control_test_id="LDR-004",
        status="processed",
    ),
]

_CORRECTIVE_ACTIONS: list[CorrectiveAction] = [
    CorrectiveAction(
        car_id="CAR-9001",
        finding_id="FND-3009",
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

_AUDIT_PACK: list[AuditPackDomain] = [
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


def open_findings_for_domain(domain: str) -> int:
    return sum(
        1 for f in _FINDINGS if f.domain == domain and f.status in OPEN_FINDING_STATUSES
    )


def synthetic_domain_statuses() -> list[DomainStatus]:
    return [
        DomainStatus(
            domain=domain,
            control_count=control_count,
            open_findings=open_findings_for_domain(domain),
            psoe=PsoeBreakdown(
                present=_DOMAIN_PSOE[domain][0],
                suitable=_DOMAIN_PSOE[domain][1],
                operating=_DOMAIN_PSOE[domain][2],
                effective=_DOMAIN_PSOE[domain][3],
            ),
        )
        for domain, control_count in _DOMAIN_CONTROL_COUNTS.items()
    ]


def synthetic_evidence() -> list[EvidenceItem]:
    return list(_EVIDENCE)


def synthetic_findings() -> list[Finding]:
    return list(_FINDINGS)


def synthetic_corrective_actions() -> list[CorrectiveAction]:
    return list(_CORRECTIVE_ACTIONS)


def synthetic_audit_pack() -> list[AuditPackDomain]:
    return list(_AUDIT_PACK)
