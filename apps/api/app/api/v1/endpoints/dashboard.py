"""Dashboard endpoints.

The payloads are still synthetic (docs/DECISIONS.md — no compliance logic in
this phase), but the routes are tenant-guarded like every other endpoint: a
caller must present a verified TenantContext, so the dashboard cannot be used
as a side channel to reach an organisation the caller has no membership in.
Synthetic figures are keyed off the resolved organisation id rather than a
client-supplied slug.
"""

from fastapi import APIRouter

from app.api.deps import CurrentTenant
from app.core.roles import Permission
from app.data.synthetic import (
    GENERATED_AT,
    OPEN_FINDING_STATUSES,
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


@router.get("/overview", response_model=AssuranceOverview)
def get_overview(context: CurrentTenant) -> AssuranceOverview:
    context.require(Permission.ORG_READ)
    return AssuranceOverview(
        organisation_id=context.organisation_id,
        generated_at=GENERATED_AT,
        high_risk_findings=sum(
            1
            for f in synthetic_findings()
            if f.severity in ("High", "Critical") and f.status in OPEN_FINDING_STATUSES
        ),
        overdue_corrective_actions=sum(
            1 for c in synthetic_corrective_actions() if c.status == "overdue"
        ),
        evidence_freshness_pct=94,
        domains=synthetic_domain_statuses(),
    )


@router.get("/evidence", response_model=list[EvidenceItem])
def get_evidence(context: CurrentTenant) -> list[EvidenceItem]:
    context.require(Permission.ORG_READ)
    return synthetic_evidence()


@router.get("/findings", response_model=list[Finding])
def get_findings(context: CurrentTenant) -> list[Finding]:
    context.require(Permission.ORG_READ)
    return synthetic_findings()


@router.get("/corrective-actions", response_model=list[CorrectiveAction])
def get_corrective_actions(context: CurrentTenant) -> list[CorrectiveAction]:
    context.require(Permission.ORG_READ)
    return synthetic_corrective_actions()


@router.get("/audit-pack", response_model=list[AuditPackDomain])
def get_audit_pack(context: CurrentTenant) -> list[AuditPackDomain]:
    context.require(Permission.ORG_READ)
    return synthetic_audit_pack()
