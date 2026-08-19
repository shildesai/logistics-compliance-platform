// Mirrors apps/api/app/schemas/*.py. Phase 1 shell — synthetic data only.

export interface Organization {
  id: string;
  name: string;
  slug: string;
}

export interface PsoeBreakdown {
  present: number;
  suitable: number;
  operating: number;
  effective: number;
}

export interface DomainStatus {
  domain: string;
  control_count: number;
  open_findings: number;
  psoe: PsoeBreakdown;
}

export interface AssuranceOverview {
  organization_slug: string;
  generated_at: string;
  high_risk_findings: number;
  overdue_corrective_actions: number;
  evidence_freshness_pct: number;
  domains: DomainStatus[];
}

export interface EvidenceItem {
  evidence_id: string;
  source_system: string;
  entity: string;
  captured_at: string;
  control_test_id: string;
  status: string;
}

export interface Finding {
  finding_id: string;
  control_test_id: string;
  domain: string;
  severity: string;
  status: string;
  confidence: number;
  affected_entity: string;
}

export interface CorrectiveAction {
  car_id: string;
  finding_id: string;
  owner: string;
  due_date: string;
  status: string;
}

export interface AuditPackDomain {
  domain: string;
  population: number;
  exceptions: number;
  status: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    path: string;
    timestamp: string;
    details?: unknown;
  };
}
