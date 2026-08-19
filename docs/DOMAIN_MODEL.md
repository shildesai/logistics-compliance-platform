# Domain Model

Source: `docs/reference/Logistics_Compliance_Intelligence_Product_Requirements_Architecture_Blueprint_v2`,
`docs/reference/Logistics_AI_SaaS_Market_Product_Business_Case_Australia_v2`,
`docs/reference/Logistics_Compliance_Intelligence_Platform_Concept_Deck_v3`,
`docs/reference/Logistics_Compliance_Control_Test_Catalogue_v2.json`.

This document defines the bounded contexts and the minimum database entities for the
platform. It is a planning document, not a schema migration — see
`docs/IMPLEMENTATION_PLAN.md` for how these map onto modules and phases.

## 1. Bounded contexts

The source docs describe one conceptual graph
(`Regulation → Obligation → Risk → Control → Evidence → Data Source → Test → Finding →
Remediation → Verification`). That graph is too large for one bounded context — it spans
regulatory reference data, operational evidence, rule execution, human review workflow,
and (later) cross-tenant sharing, each with different change cadence, consistency
requirements, and trust boundaries. Proposed contexts:

### Core domains (own the product's differentiation)

| Context | Responsibility | Key concepts |
|---|---|---|
| **Applicability & Regulatory Reference** | Decides *what applies* before anything is scored. Holds regulation source records, obligations, jurisdiction/rule-pack versions and effective dates. | Regulation, Obligation, Jurisdiction, RulePack, ApplicabilityProfile |
| **Control Catalogue** | The versioned catalogue of controls, risks and control-tests (the 54-record JSON is the seed data for this context). | Risk, Control, ControlTest |
| **Evidence** | Ingests, normalises and stores operational data as evidence with full source lineage. Owns connectors. | DataSource, Connector, EvidenceRecord, Entity masters (Driver, Vehicle, Trip, Load, Site) |
| **Test Engine** | Executes deterministic, analytical and AI-assisted tests against evidence + applicable rule packs; versions results. | TestRun, TestResult |
| **Findings & Review** | Finding lifecycle from potential to confirmed/rejected; severity, PSOE impact, human review. | Finding, ReviewAction |
| **Remediation** | Corrective Action Request (CAR) lifecycle: owner, due date, closure evidence, recurrence/effectiveness monitoring. | CorrectiveAction, EffectivenessCheck |

### Supporting domains (phase 2+, but their trust/data boundaries must be designed now)

| Context | Responsibility | Phase |
|---|---|---|
| **Audit Workspace** | Packages evidence into auditor-facing workpapers: population, samples, exceptions, comments, sign-off, export. | Phase 2 |
| **Supplier Assurance / Compliance Passport** | Supplier onboarding, certificates/insurance, governed cross-tenant sharing of assurance status to customers. | Phase 3 (data model: the 7 `SUP-*` P2 controls exist in the catalogue today) |
| **AI Copilot & Reasoning** | Grounded Q&A, document classification, root-cause hypotheses, audit narrative drafting. Wraps LLM calls; never writes a confirmed finding. | Phase 1.5 gated rollout (see Implementation Plan) |

### Generic/cross-cutting domains (used by everything, owned by no product feature)

| Context | Responsibility |
|---|---|
| **Identity & Tenancy** | Tenants/organisations, users, roles, RBAC/ABAC, SSO/SAML/OIDC, MFA. |
| **Audit Trail** | Immutable log of evidence collection, test execution, AI reasoning, human review actions and closure decisions. Every other context writes to it through one interface; nothing reads/writes it directly except via that interface. |
| **Notifications & Orchestration** | Escalations, due-date reminders, cross-context event routing (e.g. TestResult → Finding → Notification). |

### Context relationships (high level)

```
Identity & Tenancy ──────────────┐
                                  ▼
Applicability & Regulatory  →  Control Catalogue  →  Test Engine  →  Findings & Review  →  Remediation
        Reference                                        ▲                                     │
                                  Evidence ───────────────┘                                     │
                                     ▲                                                          ▼
                              Connectors/Data Sources                          Audit Workspace (P2, reads Findings+Evidence)
                                                                                Supplier Assurance (P3, reads Findings, shares outward)

AI Copilot ── reads (never writes-confirmed) ──> Findings, Evidence, Audit Trail
Audit Trail ── written by ──> Evidence, Test Engine, Findings, Remediation, AI Copilot
```

Applicability, Control Catalogue and Evidence are upstream of everything else and change
on a slow, governed cadence (regulatory/legal review). Findings, Remediation and the
Audit Trail change continuously as operations run. This split matters: the
slow-changing contexts need versioning and legal sign-off workflows; the fast-changing
ones need throughput and low-latency event handling. Conflating them (e.g. embedding a
threshold value in a Finding instead of referencing a versioned RulePack) is the most
likely modelling mistake — see `docs/DECISIONS.md`.

## 2. Minimum database entities

This is the smallest entity set that supports the Phase 1 (Operator MVP) acceptance
criteria in the blueprint (§15) without foreclosing Phase 2/3. Fields are illustrative,
not a migration spec.

### Identity & Tenancy
- **Tenant** — id, name, jurisdiction_defaults, data_residency, retention_policy_id
- **User** — id, tenant_id, email, auth_provider_ref, mfa_enabled
- **Role**, **Permission**, **UserRole** — RBAC; ABAC attributes (e.g. site/customer scoping) as a claims table rather than new tables per attribute

### Applicability & Regulatory Reference
- **Regulation** — id, jurisdiction, source_reference, effective_from, effective_to
- **Obligation** — id, regulation_id, description, applicable_roles (CoR role list)
- **RulePack** — id, jurisdiction, version, effective_from, effective_to, status (draft/active/superseded)
- **ApplicabilityProfile** — tenant_id, jurisdiction, cor_role(s), vehicle_type(s), operating_model, accreditation_status → resolves to applicable Obligation/Control set

### Control Catalogue
- **Risk** — id, description
- **Control** — id, obligation_id, risk_id, objective, owner_role, frequency, status
- **ControlTest** — id (e.g. `FAT-001`), control_id, domain, test_type (deterministic/analytical/ai), test_logic_ref, psoe_dimension, default_severity, product_phase, human_review_required, required_data_fields (jsonb)

### Evidence
- **DataSource** — id, tenant_id, system_type (TMS/EWD/Telematics/Fleet/HR-LMS/WMS/Weighbridge/Supplier-portal/GRC-DMS/CSV), connection_status
- **Driver**, **Vehicle**, **Trip**, **Load**, **Site**, **Supplier** — read-through entity masters keyed by tenant_id + source system id (see §10 of Decisions: *not* the system of record)
- **EvidenceRecord** — id, tenant_id, source_id (DataSource), source_record_id, captured_at, entity_refs (driver/vehicle/trip/load/supplier), control_test_id(s), original_value (jsonb), transformation_ref, hash, version, retention_expiry

### Test Engine
- **TestRun** — id, control_test_id, rule_pack_version, triggered_by (event/schedule), started_at, completed_at
- **TestResult** — id, test_run_id, entity_ref, evidence_refs (array), outcome (pass/exception), computed_values (jsonb), result_version

### Findings & Review
- **Finding** — id, tenant_id, control_test_id, test_result_id, severity, psoe_impact, affected_entity_ref, status (potential/confirmed/rejected), confidence, root_cause_hypothesis, evidence_bundle_refs
- **ReviewAction** — id, finding_id, reviewer_id, action, comment, acted_at

### Remediation
- **CorrectiveAction** — id, finding_id, owner_id, due_date, description, status, closure_evidence_id, recurrence_tag
- **EffectivenessCheck** — id, corrective_action_id, checked_at, recurrence_found (bool), notes

### Cross-cutting
- **AuditLogEntry** — id, tenant_id, actor_id, action, entity_type, entity_id, before, after, occurred_at, prev_hash, hash (hash-chained for tamper evidence)
- **AIOutput** — id, tenant_id, model, prompt_ref, source_evidence_refs, output, confidence, consumed_by (finding_id / query_id), human_review_status

### Deferred (schema placeholders only — do not build workflows in Phase 1)
- **SupplierProfile**, **AssurancePassport**, **PassportShare** (Phase 3)
- **WorkpaperPack**, **EvidencePopulation**, **Sample**, **AuditorComment** (Phase 2 — Phase 1 only needs a simple export of Finding+Evidence+CorrectiveAction per domain, not this model)

## 3. Notes on entity design

- **Tenant isolation** is a first-class column (`tenant_id`) on every table that holds
  customer data, enforced at the query layer (e.g. Postgres row-level security or a
  mandatory repository-layer filter), not left to application discipline alone.
- **RulePack/ControlTest versioning**: `TestResult` must reference the exact
  `rule_pack_version` used, so editing a rule pack later never changes the meaning of a
  historical result (see effective-dating risk in `docs/DECISIONS.md`).
- **Evidence vs. entity masters**: Driver/Vehicle/Trip/Load/Site/Supplier are caches of
  source-system data for the purpose of linking evidence, not an editable operational
  system of record.
