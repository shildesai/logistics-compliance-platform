import uuid

from pydantic import BaseModel


class PsoeBreakdown(BaseModel):
    present: int
    suitable: int
    operating: int
    effective: int


class DomainStatus(BaseModel):
    domain: str
    control_count: int
    open_findings: int
    psoe: PsoeBreakdown


class AssuranceOverview(BaseModel):
    organisation_id: uuid.UUID
    generated_at: str
    high_risk_findings: int
    overdue_corrective_actions: int
    evidence_freshness_pct: int
    domains: list[DomainStatus]


class ControlSummary(BaseModel):
    control_test_id: str
    domain: str
    name: str
    test_type: str
    severity: str
    status: str


class EvidenceItem(BaseModel):
    evidence_id: str
    source_system: str
    entity: str
    captured_at: str
    control_test_id: str
    status: str


class Finding(BaseModel):
    finding_id: str
    control_test_id: str
    domain: str
    severity: str
    status: str
    confidence: float
    affected_entity: str


class CorrectiveAction(BaseModel):
    car_id: str
    finding_id: str
    owner: str
    due_date: str
    status: str


class AuditPackDomain(BaseModel):
    domain: str
    population: int
    exceptions: int
    status: str
