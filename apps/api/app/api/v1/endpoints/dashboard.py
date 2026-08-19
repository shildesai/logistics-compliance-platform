from fastapi import APIRouter

from app.core.errors import NotFoundError
from app.data.synthetic import (
    GENERATED_AT,
    synthetic_audit_pack,
    synthetic_corrective_actions,
    synthetic_domain_statuses,
    synthetic_evidence,
    synthetic_findings,
)
from app.schemas.dashboard import (
    AssuranceOverview,
    AuditPackDomain,
    CorrectiveAction,
    EvidenceItem,
    Finding,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_KNOWN_ORG_SLUGS = {
    "southern-cross-logistics",
    "outback-freight-co",
    "coastal-bulk-transport",
}


def _check_org(org_slug: str) -> None:
    if org_slug not in _KNOWN_ORG_SLUGS:
        raise NotFoundError(f"Unknown organization '{org_slug}'")


@router.get("/overview", response_model=AssuranceOverview)
def get_overview(org: str = "southern-cross-logistics") -> AssuranceOverview:
    _check_org(org)
    domains = synthetic_domain_statuses()
    return AssuranceOverview(
        organization_slug=org,
        generated_at=GENERATED_AT,
        high_risk_findings=sum(1 for f in synthetic_findings() if f.severity in ("High", "Critical")),
        overdue_corrective_actions=sum(
            1 for c in synthetic_corrective_actions() if c.status == "overdue"
        ),
        evidence_freshness_pct=94,
        domains=domains,
    )


@router.get("/evidence", response_model=list[EvidenceItem])
def get_evidence(org: str = "southern-cross-logistics") -> list[EvidenceItem]:
    _check_org(org)
    return synthetic_evidence()


@router.get("/findings", response_model=list[Finding])
def get_findings(org: str = "southern-cross-logistics") -> list[Finding]:
    _check_org(org)
    return synthetic_findings()


@router.get("/corrective-actions", response_model=list[CorrectiveAction])
def get_corrective_actions(org: str = "southern-cross-logistics") -> list[CorrectiveAction]:
    _check_org(org)
    return synthetic_corrective_actions()


@router.get("/audit-pack", response_model=list[AuditPackDomain])
def get_audit_pack(org: str = "southern-cross-logistics") -> list[AuditPackDomain]:
    _check_org(org)
    return synthetic_audit_pack()
