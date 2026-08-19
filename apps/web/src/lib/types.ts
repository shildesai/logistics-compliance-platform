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

// --- Compliance Control Graph ---------------------------------------------
// Mirrors apps/api/app/schemas/control_graph.py.
//
// NOTE: `rule_configuration`, `severity_configuration` and `criteria` are
// deliberately typed as opaque records. Regulation-specific logic is evaluated
// server-side only; the UI renders these as inert data and must never branch
// on their contents (CLAUDE.md: no legal thresholds in UI code).

export type LifecycleStatus =
  | "DRAFT"
  | "IN_REVIEW"
  | "APPROVED"
  | "ACTIVE"
  | "SUPERSEDED"
  | "RETIRED";

export type ControlTestType =
  | "DETERMINISTIC"
  | "ANALYTICAL"
  | "AI_ASSISTED"
  | "MANUAL";

export type PsoeDimension = "PRESENT" | "SUITABLE" | "OPERATING" | "EFFECTIVE";

export interface VersionMeta {
  version: number;
  status: LifecycleStatus;
  effective_from: string;
  effective_to: string | null;
  source_reference: string | null;
  reviewed_by_id: string | null;
  approved_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RegulatorySource {
  id: string;
  source_code: string;
  name: string;
  publisher: string;
  url: string | null;
  document_type: string | null;
  retrieved_on: string | null;
}

export interface RegulationVersion extends VersionMeta {
  id: string;
  title: string;
  summary: string | null;
  jurisdiction_codes: string[];
  requires_control_review: boolean;
  change_note: string | null;
  regulatory_source: RegulatorySource | null;
}

export interface RegulationRef {
  id: string;
  regulation_code: string;
  name: string;
  short_name: string | null;
  regulator: string | null;
}

export interface RegulationListItem {
  regulation: RegulationRef;
  current_version: RegulationVersion | null;
}

export interface ApplicabilityRule extends VersionMeta {
  id: string;
  rule_code: string;
  name: string;
  description: string | null;
  criteria: Record<string, unknown>;
}

export interface GraphRisk extends VersionMeta {
  id: string;
  risk_code: string;
  name: string;
  description: string;
  inherent_likelihood: string | null;
  inherent_consequence: string | null;
}

export interface GraphObligation extends VersionMeta {
  id: string;
  obligation_code: string;
  regulation_id: string;
  name: string;
  description: string;
  cor_role_codes: string[];
}

export interface ObligationDetail extends GraphObligation {
  regulation: RegulationRef;
  risks: GraphRisk[];
  applicability_rules: ApplicabilityRule[];
}

export interface ControlVersion extends VersionMeta {
  id: string;
  name: string;
  objective: string;
  owner_type: string;
  frequency: string;
  automation_level: string;
  psoe_relevance: PsoeDimension[];
  procedure_reference: string | null;
  change_note: string | null;
}

export interface ControlRef {
  id: string;
  control_code: string;
  domain: string;
}

export interface ControlListItem {
  control: ControlRef;
  current_version: ControlVersion | null;
}

export interface EvidenceRequirement extends VersionMeta {
  id: string;
  requirement_code: string;
  name: string;
  description: string | null;
  source_type: string;
  required_fields: string[];
  is_mandatory: boolean;
  max_age_days: number | null;
}

export interface RemediationTemplate extends VersionMeta {
  id: string;
  template_code: string;
  title: string;
  description: string;
  suggested_steps: string[];
  default_owner_type: string;
  default_due_days: number;
  requires_closure_evidence: boolean;
  requires_effectiveness_check: boolean;
}

export interface ControlTestVersion extends VersionMeta {
  id: string;
  name: string;
  test_logic_description: string;
  test_type: ControlTestType;
  rule_configuration: Record<string, unknown>;
  severity_configuration: Record<string, unknown>;
  human_review_required: boolean;
  psoe_impact: PsoeDimension[];
  change_note: string | null;
}

export interface ControlTestDetail {
  control_test: { id: string; test_code: string };
  current_version: ControlTestVersion | null;
  evidence_requirements: EvidenceRequirement[];
  remediation_templates: RemediationTemplate[];
}

export interface ControlDetail {
  control: ControlRef;
  current_version: ControlVersion | null;
  risks: GraphRisk[];
  tests: ControlTestDetail[];
}

export interface LineagePath {
  regulation: RegulationRef;
  regulation_version: RegulationVersion | null;
  obligation: GraphObligation;
  applicability_rules: ApplicabilityRule[];
  risk: GraphRisk;
  is_primary_control: boolean;
}

export interface ControlLineage {
  control: ControlRef;
  current_version: ControlVersion | null;
  paths: LineagePath[];
  control_version_history: ControlVersion[];
  test_version_history: Record<string, ControlTestVersion[]>;
}

export interface GraphStatistics {
  regulations: number;
  obligations: number;
  controls: number;
  control_tests: number;
  active_control_versions: number;
}
