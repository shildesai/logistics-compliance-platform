// Mirrors apps/api/app/schemas/. Phase 1 shell — see docs/IMPLEMENTATION_PLAN.md
// on generating this from the OpenAPI schema instead of maintaining it by hand.

export type Role =
  | "PLATFORM_ADMIN"
  | "ORG_ADMIN"
  | "COMPLIANCE_MANAGER"
  | "OPERATIONS_MANAGER"
  | "EXECUTIVE"
  | "AUDITOR"
  | "READ_ONLY";

export type Permission =
  | "org:read"
  | "org:manage"
  | "members:manage"
  | "applicability:manage"
  | "operations:manage"
  | "platform:admin";

export interface Organisation {
  id: string;
  name: string;
  slug: string;
  status: string;
}

export interface Membership {
  organisation: Organisation;
  role: Role;
  permissions: Permission[];
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  is_platform_admin: boolean;
  memberships: Membership[];
}

export interface OrganisationProfile {
  id: string;
  name: string;
  slug: string;
  legal_name: string | null;
  abn: string | null;
  status: string;
}

export interface OrganisationMember {
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
}

export interface Jurisdiction {
  id: string;
  code: string;
  name: string;
  hvnl_participant: boolean;
}

export interface AssignedJurisdiction {
  id: string;
  jurisdiction: Jurisdiction;
}

export interface CoRRole {
  id: string;
  code: string;
  name: string;
  description: string | null;
}

export interface AssignedCoRRole {
  id: string;
  cor_role: CoRRole;
  notes: string | null;
}

export type AccreditationStatus =
  | "NOT_ACCREDITED"
  | "APPLIED"
  | "ACCREDITED"
  | "SUSPENDED"
  | "EXPIRED"
  | "WITHDRAWN";

export interface Accreditation {
  id: string;
  scheme: string;
  module: string;
  status: AccreditationStatus;
  accreditation_number: string | null;
  valid_from: string | null;
  valid_to: string | null;
  notes: string | null;
}

export interface Site {
  id: string;
  name: string;
  code: string;
  site_type: string;
  jurisdiction_id: string | null;
  business_unit_id: string | null;
  suburb: string | null;
  postcode: string | null;
  is_active: boolean;
}

export interface Fleet {
  id: string;
  name: string;
  code: string;
  business_unit_id: string | null;
  home_site_id: string | null;
  vehicle_count: number;
  is_active: boolean;
}

export interface Supplier {
  id: string;
  name: string;
  code: string;
  abn: string | null;
  supplier_type: string;
  is_active: boolean;
}

export interface BusinessUnit {
  id: string;
  name: string;
  code: string;
  parent_id: string | null;
  is_active: boolean;
}

// --- Dashboard ------------------------------------------------------------

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
  organisation_id: string;
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
