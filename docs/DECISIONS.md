# Decisions

Source: `docs/reference/Logistics_Compliance_Intelligence_Product_Requirements_Architecture_Blueprint_v2`,
`docs/reference/Logistics_AI_SaaS_Market_Product_Business_Case_Australia_v2`,
`docs/reference/Logistics_Compliance_Intelligence_Platform_Concept_Deck_v3`,
`docs/reference/Logistics_Compliance_Control_Test_Catalogue_v2.json`.

This document records things in the source material that should **not** be implemented
literally, and the reasoning behind key architecture choices in
`docs/IMPLEMENTATION_PLAN.md` and `docs/DOMAIN_MODEL.md`. Treat it as a living log —
append new entries rather than rewriting history, in keeping with the platform's own
"never silently rewrite the past" principle.

## 1. Things not to implement literally

### 1.1 "48 structured control tests" is wrong — the catalogue has 54
The blueprint (§6, §15) and business case both say "48 control tests." The actual JSON
catalogue (`Logistics_Compliance_Control_Test_Catalogue_v2.json`) contains **54**
records: 47 tagged `product_phase: P1` across the 8 MVP domains, and 7 tagged `P2`
under `Supplier / CoR Assurance`. Do not hard-code "48" anywhere (docs, UI counters,
acceptance-criteria checks, test names). Treat the JSON file as the single source of
truth and count/derive from it programmatically. This document and
`docs/IMPLEMENTATION_PLAN.md` use the verified counts (54 total / 47 P1 / 7 P2).

### 1.2 The catalogue's "Rule" test_type is not a distinct engine
Two records (`FAT-006`, `FAT-007`) are tagged `test_type: "Rule"` while 35 others doing
functionally identical threshold/expiry/override checks are tagged `"Deterministic"`.
This reads as an inconsistency in how the catalogue was authored, not an intentional
third execution model. Build one deterministic rule engine and normalize `"Rule"` into
it — but record that normalization here rather than silently guessing, since a future
catalogue revision may reintroduce a real distinction (e.g. "Rule" = configurable by a
compliance manager without a code change, vs. "Deterministic" = fixed logic). Revisit if
that turns out to be the intent.

### 1.3 `test_logic` strings are placeholders, not specs
Every catalogue entry has a one-sentence `test_logic` (e.g. *"Calculate actual work time
against configured effective-dated fatigue rule pack"*). This is illustrative, not
executable. Do not transliterate these sentences directly into code or SQL. Each of the
54 tests needs its own short design pass — exact thresholds, timezone handling,
multi-leg/multi-driver trips, what counts as "missing" vs. "not yet due" — ideally with
sign-off from whoever owns HVNL/CoR interpretation, before it is encoded into a
versioned `RulePack`. Treat every test as "needs specification," not "ready to build,"
even though the catalogue looks implementation-ready.

### 1.4 The "20-control catalogue" (deck slide 9) is not MVP scope
The concept deck lists 20 future-state controls (induction, contractor onboarding,
loading/unloading safety, CoR responsibilities, risk assessments, record retention, SMS
review, executive due diligence, regulatory change, etc.). Only the 8-domain / 54-test
JSON catalogue is implementation-ready for Phase 1. Do not build schema or UI for the
other 12 items on that slide as if they were in scope now — they are a roadmap
placeholder, not a spec.

### 1.5 "≥25 deterministic / ≥10 analytical tests" is a floor, not a target
Blueprint §15's MVP acceptance criteria ("Can run at least 25 deterministic tests and 10
analytical tests") reads like a minimum bar carried over from an earlier draft. The
current catalogue already exceeds it (35 deterministic + 2 rule, 15 analytical, all in
P1). Don't scope Phase 1 down to exactly 25/10 — build against the full P1 catalogue and
treat the acceptance criteria as satisfied, not as a ceiling.

### 1.6 HVA "whole-of-business SMS assessment from 1 Aug 2026" needs verification
Deck slide 6 states HVA introduces a whole-of-business SMS assessment and PSOE-based
audits "from 1 Aug 2026," with no further detail anywhere in the source set. Do not
implement specific SMS/PSOE-audit workflow logic against this claim without verifying
current NHVR guidance directly (the blueprint's own source list is NHVR's public pages —
check them, don't assume the deck's paraphrase is current or complete). Treat as a
regulatory fact requiring independent confirmation, not an implementation spec.

### 1.7 WA/NT are future, separate rule packs — don't fold them into HVNL now
Both the blueprint (§5) and business case call out WA/NT as "future separate rule
packs" explicitly excluded from the current HVNL-based catalogue. Keep the applicability
engine's `RulePack` model jurisdiction-scoped so this is a config addition later, but do
not build WA/NT rule content, thresholds, or applicability logic now — there is no
source material to base it on, and guessing would produce wrong results in exactly the
domain (heavy vehicle safety) where wrong results carry the most risk.

### 1.8 AI-assisted tests and "Ask Compliance" are unsafe to ship at the same bar as deterministic tests
`LDR-002`/`LDR-003` (image-based) and the "Ask Compliance" screen are listed under P1/
MVP scope in the source docs, but the same docs also state AI outputs need grounding,
confidence, and human review, and must never auto-close a finding. Shipping these on the
same timeline as deterministic tests — which have no hallucination risk — treats a
qualitatively different risk as if it were just "more scope." Gate them behind a
dedicated Phase 1.5 evaluation pass (see Implementation Plan §7) rather than bundling
into the Phase 1 exit criteria.

### 1.9 Business-case pricing/market figures are not product inputs
Pricing hypotheses (A$750–$6k/month, A$50k–$250k+/year, etc.), market sizing, and GTM
timelines are commercial planning inputs. They must not leak into product code,
configuration, feature flags, or public-facing copy without commercial sign-off, and
have no corresponding database entity — they are out of scope for this repository's
application code entirely.

### 1.10 Positioning guardrails are copy constraints, not technical requirements, but engineers building UI text need to know them
"Avoid clone-style analogies," "AI does not replace auditors," "HVA is not mandatory for
everyone," "no single opaque compliance score" are brand/positioning rules from the
business case and deck (§12 / slide 30). They don't produce database entities, but they
do constrain UI copy and API response shaping — e.g. a dashboard must never render a
top-level compliance percentage without a path to the underlying evidence. Recorded here
so the constraint isn't lost between the marketing document and the engineering team.

### 1.11 Vehicle/Driver/Trip data is not this platform's system of record
The source docs are explicit that this product is "not a TMS replacement." Don't design
Driver/Vehicle/Trip/Load/Site tables as authoritative, user-editable masters — they are
read-through copies of source-system data, keyed by tenant + source system + source
record id, editable only for compliance-specific annotations (e.g. a reviewer's note),
never for the underlying operational fact.

### 1.12 Supplier "Compliance Passport" sharing is not a simple visibility flag
Phase 3's cross-tenant sharing (a supplier's assurance status visible to specific
customers) is the first place two different tenants' data intentionally touch. Resist
the temptation to bolt this on later as `is_shared: true` on an existing tenant-scoped
table — it needs its own authorization model (governed, partial, revocable, auditable)
designed when Phase 3 actually starts, informed by real supplier/customer contracts, not
guessed now.

## 2. Key architecture decisions

### 2.1 Modular monolith, not microservices, for Phase 0–2
**Decision:** one FastAPI deployable, organised into modules matching the bounded
contexts in `docs/DOMAIN_MODEL.md`, backed by a single PostgreSQL database.
**Why:** the domain boundaries most likely to move (Phase 2 Audit Workspace, Phase 3
Supplier Assurance) are design hypotheses with zero design-partner validation yet.
Microservice overhead (network calls for what would otherwise be a transaction, e.g.
Finding→CAR creation, distributed tracing, service mesh) isn't justified before that
validation exists, and cross-context dashboard queries (Assurance Overview joining
Controls+Findings+Evidence) are cheaper in one database. Module boundaries are still
enforced in code (service-layer-only cross-module calls, import-linter checks) so a
future extraction of a genuinely high-load module (evidence ingestion, AI copilot)
remains possible without a rewrite.

### 2.2 CSV/Excel connector before any live system integration
**Decision:** Phase 0 builds the CSV/Excel fallback ingestion path first, ahead of live
TMS/EWD/telematics/fleet API connectors.
**Why:** it's the lowest-integration-risk path to real evidence, unblocks design-partner
pilots and the deterministic/analytical engines before any partner's API access is
negotiated, and every live connector will eventually need a fallback anyway per the
blueprint's own P0 integration table.

### 2.3 Deterministic and analytical tests run on different execution models
**Decision:** deterministic (and "Rule") tests run synchronously/near-real-time as
evidence is ingested; analytical tests run on a scheduled/windowed background job.
**Why:** the catalogue's analytical tests (e.g. `SCH-002` speed-events-correlate-with-
loading-delay) are inherently about patterns over a time window, not a single event —
forcing them through a per-event execution path either produces wrong results (no window
to compare against) or forces artificial batching of deterministic tests that don't need
it. See `docs/IMPLEMENTATION_PLAN.md` §8.

### 2.4 Rule packs are versioned and immutable once active; results pin a version
**Decision:** `RulePack` edits always create a new version; a `TestResult` always
records the exact version it was evaluated against; nothing may mutate a `TestResult`
retroactively by changing the rule pack it once referenced.
**Why:** this is required by the source docs' own principle ("regulatory rules must be
versioned and effective-dated") and is the only way to guarantee a historical audit pack
stays accurate after a rule pack is later corrected or updated.

### 2.5 AI output is structurally separated from confirmed compliance determinations
**Decision:** AI-originated writes can only ever create `PotentialFinding`/`AIOutput`
records; there is no code path — not a permission check alone, a data-model constraint —
by which an AI-originated write can set `Finding.status = confirmed` or close a CAR.
**Why:** the source docs state this as a non-negotiable product principle ("never allow
AI to make a final legal or regulatory compliance determination"); enforcing it only in
application logic or UI is not durable enough for a platform whose evidentiary
credibility is the whole product.

### 2.6 Tenant isolation enforced at the query layer, not by convention
**Decision:** every tenant-scoped table carries `tenant_id`; isolation is enforced
structurally (e.g. Postgres row-level security or a mandatory repository-layer filter
applied by the framework, not by each handler remembering to filter), with automated
cross-tenant-leak tests from Phase 0.
**Why:** this platform holds safety-critical and potentially litigation-relevant data
for competing operators, suppliers and shippers on one instance; an isolation bug here
is categorically worse than in most SaaS products.
