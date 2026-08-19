# Implementation Plan

Source: `docs/reference/Logistics_Compliance_Intelligence_Product_Requirements_Architecture_Blueprint_v2`,
`docs/reference/Logistics_AI_SaaS_Market_Product_Business_Case_Australia_v2`,
`docs/reference/Logistics_Compliance_Intelligence_Platform_Concept_Deck_v3`,
`docs/reference/Logistics_Compliance_Control_Test_Catalogue_v2.json`.

See also `docs/DOMAIN_MODEL.md` (bounded contexts, entities) and `docs/DECISIONS.md`
(architectural/regulatory decisions and things to *not* implement literally). This
document does not implement the application — it is the plan for doing so.

## 1. Technical summary

The platform is a multi-tenant SaaS that turns operational logistics data (TMS, EWD,
telematics/GPS, fleet maintenance, HR/LMS, WMS, weighbridge/permit register, supplier
systems, GRC/DMS) into compliance evidence, and continuously tests that evidence against
versioned, effective-dated regulatory rule packs (Australian HVNL / Chain of
Responsibility / Heavy Vehicle Accreditation, initially). It is not a TMS, not a generic
GRC tool, and not an automated auditor — it interprets data that other systems already
produce.

The core abstraction is the **Compliance Control Graph**:
`Regulation → Obligation → Risk → Control → Evidence → Data Source → Test → Finding →
Remediation → Verification`, gated by an **Applicability Engine** that determines which
obligations/controls apply to a given tenant *before* any test runs (based on
jurisdiction, CoR role, vehicle type, accreditation status and operating model).
Assurance is expressed per-control as **PSOE** (Present / Suitable / Operating /
Effective), never as a single opaque score.

Three governing constraints shape every architectural choice below:
1. AI may produce potential findings and analysis; it may never make a final
   compliance/legal determination or auto-close a material finding.
2. Every finding and evidence item must carry traceable lineage and an immutable audit
   trail.
3. Regulatory thresholds must live in versioned, effective-dated configuration, never
   hard-coded in application or UI code.

## 2. MVP capabilities

Derived from blueprint §6, §15 and the concept deck's Phase 1 slide. In scope for the
Operator MVP:

- **Applicability v1** — resolve applicable obligations/controls from jurisdiction, CoR
  role, vehicle type and accreditation status (foundation, not full breadth).
- **Evidence ingestion** for P0 data sources — TMS, EWD/work diary, Telematics/GPS, Fleet
  maintenance — plus a CSV/Excel fallback connector (build this first: lowest
  integration risk, unblocks every downstream module and design-partner pilots).
- **Control catalogue** for the 8 P1 domains (47 P1 control tests — see §9; the source
  docs' "48" figure does not match the catalogue and should not be treated as a target).
- **Deterministic rule engine** covering the 35 `Deterministic` + 2 `Rule`-type P1 tests.
- **Analytical engine** covering the 15 `Analytical`-type P1 tests (pattern/correlation
  over a rolling window, not per-event).
- **Findings workflow** — potential findings with evidence bundle, severity, PSOE
  impact, confidence; human confirm/reject; nothing auto-closes.
- **Remediation (CAR) workflow** — owner, due date, closure evidence, recurrence/
  effectiveness monitoring.
- **Lightweight audit pack export** for ≥5 control domains (a Finding+Evidence+CAR
  export per domain — *not* the full Phase 2 Audit Workspace with sampling/auditor
  collaboration).
- **PSOE dashboard** by control/domain, evidence freshness, overdue CARs.
- **Immutable audit trail** for evidence, tests, reviews, remediation.
- **Security baseline** — tenant isolation, RBAC/ABAC, MFA/SSO, encryption in transit/
  at rest.
- 6 of the 7 MVP screens: Assurance Overview, Control Explorer, Findings Inbox, Evidence
  Explorer, Corrective Actions, (lightweight) Audit Readiness.

**Explicitly deferred out of the initial MVP cut** (see Phase 1.5 in §8):
- The 2 `AI`-type tests (`LDR-002`, `LDR-003`, both image-based).
- "Ask Compliance" grounded Q&A (7th MVP screen).
- Full Audit Workspace (Phase 2), Supplier Assurance/Compliance Passport (Phase 3, the
  7 `SUP-*` P2 tests), WA/NT rule packs, WHS/dangerous goods/environmental (Phase 4),
  multi-party network (Phase 5).

**Non-goals (explicit in source docs):** TMS replacement, legal certification,
automated auditor judgement, all-regulations coverage, universal HVA-mandatory claims.

## 3. Minimum database entities

See `docs/DOMAIN_MODEL.md` §2 for the full list. Summary of what must exist before
Phase 1 can start: Tenant/User/Role, Regulation/Obligation/RulePack/ApplicabilityProfile,
Risk/Control/ControlTest, DataSource + entity masters (Driver/Vehicle/Trip/Load/Site/
Supplier) + EvidenceRecord, TestRun/TestResult, Finding/ReviewAction,
CorrectiveAction/EffectivenessCheck, AuditLogEntry, AIOutput (schema only, unused until
Phase 1.5).

## 4. Major architectural risks

| Risk | Why it matters | Mitigation direction |
|---|---|---|
| Applicability engine correctness | Wrong applicability = wrong obligations shown = compliance and trust failure; jurisdiction × CoR role × vehicle × accreditation is combinatorial | Model as explicit, testable rules with golden-case tests per role/jurisdiction combination; never a fallback "applies to everyone" default |
| Integration/connector burden | TMS/EWD/telematics/fleet systems are heterogeneous, often API-poor; many customers will start on CSV/Excel | Build the CSV/Excel path first as the common denominator; treat each live connector as its own maintenance-cost line item, not a one-off build |
| Evidence lineage & immutability at scale | Audit-grade evidence needs tamper-evidence and full traceability without runaway storage cost | Hash/version every EvidenceRecord; separate hot (queryable) and cold (retained) storage early rather than retrofitting |
| Rule/effective-date versioning | Editing a rule pack must never retroactively change a historical result used in a prior audit | TestResult pins the exact rule_pack_version; rule pack edits create a new version, never mutate in place (bitemporal, not just soft-versioned) |
| AI reliability & grounding | Hallucinated or ungrounded output in Ask Compliance / AI-assisted tests can produce false or misleading findings | Isolate AI behind its own module (`ai_copilot`); structurally prevent it from writing anything but `PotentialFinding`/`AIOutput`; gate rollout behind evaluation (Phase 1.5) |
| Multi-tenant isolation | Competing operators/suppliers/shippers share one platform; a leak is catastrophic, not just embarrassing | tenant_id on every row + enforced at the query layer (e.g. RLS), isolation covered by automated tests from day one |
| Continuous-test throughput | "Continuous" implies event-driven evaluation on thousands of trips/day, not nightly batch, or the product's core promise breaks | Deterministic tests run on evidence-ingestion events; analytical tests run on a scheduled/windowed job; don't force everything through one execution model |
| Underspecified test logic | Catalogue's `test_logic` field is a one-line natural-language placeholder per test, not an executable spec | Each of the 54 tests needs its own design pass (thresholds, edge cases, timezones, multi-leg trips) before being encoded — see Decisions §match |
| Audit Workspace retrofit | Phase 2 needs "population" and "sample" concepts that Phase 1's Finding/Evidence model doesn't require | Reserve schema names now (see Domain Model "deferred" entities) without building the workflow, so Phase 2 extends rather than rebuilds |
| Supplier Passport trust boundary | Phase 3 introduces the first cross-tenant data share; retrofitting this onto tenant-isolated tables is risky | Treat governed sharing as its own authorization model from the first design pass, even though it isn't built until Phase 3 |

## 5. Regulatory/compliance design risks

| Risk | Design implication |
|---|---|
| Hard-coded legal thresholds | Every threshold (fatigue hours, mass limits, licence-expiry windows) lives in a versioned `RulePack`, never in code or UI copy |
| AI making a final determination | Enforce at the data-model/permission level: no code path lets an AI-originated write set `Finding.status = confirmed` |
| Silent auto-closure of material findings/CARs | Workflow engine requires a human `ReviewAction`/closure evidence before a high-severity Finding or CAR can close — enforced server-side, not just a UI convention |
| Overstating HVA as mandatory | Applicability engine and UI copy must never default to "applies to everyone"; HVA is voluntary, CoR is broader and role-based — these are modelled as separate applicability dimensions, not one flag |
| Single opaque compliance score | PSOE must always be explorable to the underlying control/evidence/test; explicitly called out in source docs as "bad product behaviour" |
| Effective-dating mistakes | A rule pack update must not alter the meaning of past `TestResult`s; see versioning mitigation above |
| Evidence integrity/defensibility | Hash + version metadata on every `EvidenceRecord`, or evidence isn't defensible in an audit dispute |
| Cross-tenant leakage via Compliance Passport | Supplier sharing is deliberately partial and governed; a modelling shortcut here could over-expose one tenant's operational data to another (potentially a competitor) |
| Jurisdictional scope creep | Catalogue is HVNL-based; WA/NT are explicitly called out as future *separate* rule packs — implementing them inside the primary rule pack would silently produce wrong results there |
| Sensitive data retention | Driver fitness declarations and incident data need per-jurisdiction/per-contract retention, not one global policy |

## 6. Proposed architecture: modular monolith

**Why not microservices:** the domain boundaries above (Phase 2/3 contexts especially)
are still design hypotheses, not proven boundaries — this repo has no design-partner
validation yet. Microservice operational overhead (service mesh, distributed tracing,
cross-service transactions for a workflow like Finding→CAR→Notification) isn't justified
before that validation happens, and a monolith doesn't foreclose extracting a genuinely
high-load or high-isolation module (evidence ingestion, AI copilot) later once real
traffic patterns are known.

**Shape**, aligned to the stack already declared in `CLAUDE.md` (Next.js/React/TS
frontend, Python/FastAPI/SQLAlchemy/PostgreSQL backend) and the repo scaffold already in
place (`apps/web`, `apps/api`, `packages/shared`):

- **One deployable FastAPI service** (`apps/api`) internally organised into modules that
  mirror the bounded contexts in `docs/DOMAIN_MODEL.md`:
  `identity`, `applicability`, `catalogue`, `evidence`, `testing`, `findings`,
  `remediation`, `audit_trail`, `notifications`, plus stub modules `audit_workspace`,
  `supplier_assurance`, `ai_copilot` created empty/flagged-off in Phase 0 so their
  namespaces and schema placeholders exist without their workflows being built.
- Each module owns `router.py` (FastAPI), `service.py`, `repository.py` (SQLAlchemy),
  `models.py`, `schemas.py` (Pydantic). Cross-module calls go through a module's
  `service` layer only — never directly through another module's `repository`/ORM
  models — enforced with an import-linter–style boundary check in CI.
- **Single PostgreSQL database**, one schema (or Postgres schema-per-module if the team
  prefers stronger enforcement) with row-level tenant isolation. This keeps
  cross-context queries (e.g. an Assurance Overview dashboard joining Findings +
  Controls + Evidence freshness) cheap, which a service-per-context split would not.
- **In-process event bus / outbox pattern** for cross-module workflows (evidence
  ingested → deterministic test triggered → finding created → notification sent),
  rather than direct synchronous coupling between modules.
- **Background worker** (Celery/RQ or an async task queue, Postgres- or Redis-backed) for
  connector polling, analytical (windowed) test runs, and AI calls — kept out of the
  request/response path.
- **`packages/shared`** holds cross-cutting types used by both `apps/web` and `apps/api`
  (tenant context shape, PSOE enum, severity enum, generated OpenAPI/TS client) so the
  frontend and backend can't drift on these contracts.
- **`apps/web`** (Next.js) consumes the FastAPI service over REST/OpenAPI; no direct
  database access from the frontend.

This keeps infrastructure minimal for Phase 0/1 (no message broker, no service mesh)
while the module boundaries mean the codebase is *already* organised the way a future
service split would need it to be, should that become necessary.

## 7. Phased implementation plan

Numbering matches the product roadmap in the source docs (blueprint §14, business case
§10, deck slide 24); this section adds the engineering breakdown.

### Phase 0 — Foundation
- Identity & tenancy module, auth (SSO/OIDC), RBAC/ABAC, MFA
- Immutable audit trail infrastructure (hash-chained log), used by every later module
- Applicability engine v1 (schema + rules), seeded from `compliance/regulations`
- Control catalogue import: load the 54-record JSON into `catalogue` tables, versioned
- Evidence schema + CSV/Excel ingestion connector (first, before any live API connector)
- Security baseline: encryption in transit/at rest, tenant-isolation test suite
- CI, environments, design-partner validation loop

### Phase 1 — Operator MVP
- P0 live connectors: TMS, EWD, Telematics/GPS, Fleet maintenance (real integration or
  high-fidelity sandbox per design partner, CSV fallback remains available)
- Deterministic engine: 35 `Deterministic` + 2 `Rule` P1 tests
- Analytical engine: 15 `Analytical` P1 tests (windowed/scheduled)
- Findings module: potential-finding generation, human review workflow
- Remediation module: CAR lifecycle, closure evidence, recurrence monitoring
- 6 MVP screens (Assurance Overview, Control Explorer, Findings Inbox, Evidence
  Explorer, Corrective Actions, lightweight Audit Readiness export)
- Exit criteria: mirrors blueprint §15 acceptance criteria minus AI/Ask Compliance items

### Phase 1.5 — AI-assisted tests + Ask Compliance (gated)
- Called out separately because the source docs' own AI guardrails (no auto-close, full
  grounding, human review of material findings) need a dedicated evaluation pass before
  customer-facing use, not just a feature flag
- `ai_copilot` module: grounded Q&A restricted to permitted evidence; the 2 `LDR-*`
  AI-assisted image tests
- Exit criteria: red-team/evaluation pass showing no ungrounded or auto-confirmed output

### Phase 2 — Audit Workspace
- Auditor role/permissions, evidence population + sampling data model, workpaper
  comments, evidence requests, findings sign-off, export

### Phase 3 — Supplier Assurance
- Supplier/passport module, 7 P2 `SUP-*` controls, governed cross-tenant sharing,
  supplier dashboard, customer-specific obligation mapping

### Phase 4 — Expanded Compliance
- WHS, dangerous goods, environmental/customer-standard modules; WA/NT as separate rule
  packs (configuration, not new code paths)

### Phase 5 — Compliance Network
- Multi-party assurance relationships across enterprise shippers, 3PLs, carriers,
  subcontractors

## 8. Mapping the control-test catalogue into the architecture

The catalogue (`compliance` reference JSON) contains **54 tests across 9 domains**, not
48 (see `docs/DECISIONS.md` §1). 47 are `product_phase: P1` (the 8 MVP domains below);
7 are `P2` (`Supplier / CoR Assurance`).

| Domain | Tests | Test-type split | Phase | Primary module(s) |
|---|---|---|---|---|
| Fatigue / Work-Rest | 8 | Det 4, Analytical 2, Rule 2 | P1 | `testing` (deterministic + analytical), fed by EWD/TMS/HR-LMS/Driver-app evidence |
| Fitness to Drive | 4 | Det 3, Analytical 1 | P1 | `testing`, fed by Driver-app/TMS/Incident/HR |
| Scheduling & Speed Risk | 6 | Analytical 6 | P1 | `testing` (analytical only — all 6 require windowed correlation across TMS/Telematics/EWD/WMS/Customer portal) |
| Vehicle Maintenance & Roadworthiness | 6 | Det 5, Analytical 1 | P1 | `testing`, fed by Fleet maintenance/Driver-app/TMS/DMS |
| Mass & Dimension | 6 | Det 5, Analytical 1 | P1 | `testing`, fed by TMS/WMS/Weighbridge/Permit register/Vehicle master |
| Load Restraint | 6 | Det 2, Analytical 2, AI 2 | P1 (AI tests deferred to Phase 1.5) | `testing` + `ai_copilot` for `LDR-002`/`LDR-003` |
| Driver Competency | 5 | Det 5 | P1 | `testing` (deterministic only), fed by HR/LMS/Driver-app/TMS/Supplier portal |
| Incidents & Corrective Actions | 6 | Det 5, Analytical 1 | P1 | `testing` + `remediation` (this domain *is* the remediation feedback loop) |
| Supplier / CoR Assurance | 7 | Det 6, Analytical 1 | **P2** | `supplier_assurance` (Phase 3) — no Phase 1 work beyond reserving the schema |

Execution model by test type:
- **Deterministic (35) + Rule (2)** — functionally identical (threshold/expiry/status/
  override checks); run synchronously/near-real-time as evidence is ingested. Treat
  "Rule" as a labelling inconsistency in the source catalogue, not a separate engine
  (see `docs/DECISIONS.md`).
- **Analytical (15)** — pattern/clustering/correlation over a rolling window (e.g.
  repeat exceptions by driver/site, speed-events-after-loading-delay correlation);
  cannot run per-event, needs scheduled/windowed execution in the background worker.
- **AI (2)** — both are the image-based Load Restraint tests (`LDR-002` photo quality,
  `LDR-003` restraint-method mismatch); routed through `ai_copilot`, always land as
  `PotentialFinding`, never auto-confirmed; deferred to Phase 1.5.

Every test type produces the same `Finding` shape regardless of origin, so `findings`,
the UI, and the audit-pack export never need to special-case AI vs. deterministic
results — only the `AIOutput` provenance record differs.

Connector priority derived from this mapping: TMS, EWD, Telematics and Fleet
maintenance (P0) between them feed 6 of the 8 P1 domains directly, confirming the
blueprint's P0 integration priority is correct and should be built first.
