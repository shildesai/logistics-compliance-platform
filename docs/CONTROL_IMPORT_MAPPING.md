# Control Catalogue Import Mapping

How `docs/reference/Logistics_Compliance_Control_Test_Catalogue_v2.json` maps
into the Compliance Control Graph (`docs/DOMAIN_MODEL.md`,
`apps/api/app/models/`).

**Source of record**

| | |
|---|---|
| File | `docs/reference/Logistics_Compliance_Control_Test_Catalogue_v2.json` |
| Catalogue version | `2.0` |
| Catalogue date | `2026-08-18` |
| SHA-256 | `eb2a60810475f38c9e48e54a4fbe705e28becf1ad1e6a1dc47105bf4ac7a8602` |
| Entries | 54 |

---

## 0. The three findings that shape this mapping

Read these before the field table; they explain why the importer looks
conservative.

### 0.1 The 54 entries are control **tests**, not controls

The JSON array is named `controls`, but each entry carries both a
`control_test_id` (54 distinct) and a `control` (9 distinct). The entries are
tests; the controls are the 9 values of `control`.

Verified grouping — within each domain, `obligation`, `risk` and `control` are
strictly 1:1:1:

| Domain | Tests | Code prefix |
|---|--:|---|
| Fatigue / Work-Rest | 8 | `FAT` |
| Fitness to Drive | 4 | `FIT` |
| Scheduling & Speed Risk | 6 | `SCH` |
| Vehicle Maintenance & Roadworthiness | 6 | `MNT` |
| Mass & Dimension | 6 | `MDL` |
| Load Restraint | 6 | `LDR` |
| Driver Competency | 5 | `DRV` |
| Incidents & Corrective Actions | 6 | `CAR` |
| Supplier / CoR Assurance | 7 | `SUP` |

So one import produces **9 Controls and 54 ControlTests**, not 54 Controls.
Importing each entry as a Control would create nine duplicated fatigue
controls and destroy the shared-control architecture.

### 0.2 The catalogue contains no thresholds at all

**Zero of the 54 `test_logic` strings contain a single digit.** There are no
limits, no time windows, no comparison operators anywhere in the source:

```
FAT-001  Calculate actual work time against configured effective-dated fatigue rule pack.
FAT-004  Identify assignments where projected work will exceed remaining safe/legal window.
MDL-001  Calculated/actual gross mass exceeds configured limit/permit.
```

Each says *that* a limit is compared, never *what* the limit is. The catalogue
is a specification of intent, not an executable rule set — consistent with
`docs/DECISIONS.md` §1.3, which already recorded `test_logic` as a placeholder.

**Consequence:** `ControlTestVersion.rule_configuration` cannot be derived.
Every imported test gets `{"kind": "UNSPECIFIED", ...}` carrying the source
sentence verbatim. Writing `{"limit_minutes": 720}` would be inventing a legal
threshold — forbidden by the brief and by CLAUDE.md ("Never hard-code legal
thresholds"; "no threshold should be invented"). `UNSPECIFIED` is not a known
engine `kind`, so an imported test is **structurally unable to execute** until
a specialist specifies it.

### 0.3 `regulation_layer` and `applicability_notes` are constant boilerplate

Both fields hold one identical value across all 54 entries:

- `regulation_layer` = `"HVNL / CoR / HVA where applicable"`
- `applicability_notes` = `"Determined by jurisdiction, activity, CoR role, vehicle type, operating model and accreditation status."`

Neither carries per-entry information, so neither can drive per-obligation
attribution or applicability criteria. Both are imported as provenance plus a
`NEEDS_REVIEW` flag, never as derived logic.

The `regulation_layer` string is additionally **three frameworks in one**, and
they are not equivalent:

- **HVNL** — the law.
- **CoR** — a duty framework *within* the HVNL, not a separate instrument.
- **HVA** — a **voluntary** accreditation scheme, not law.

The importer attributes obligations to **HVNL only**. Attributing any
obligation to HVA would imply accreditation is mandatory, which it is not —
see `docs/TENANCY.md` §6 and `app/models/accreditation.py`.

---

## 1. Entity-level mapping

| Source grouping | Target entity | Cardinality |
|---|---|--:|
| (constant) `regulation_layer` | `Regulation` + `RegulationVersion` (HVNL) | 1 |
| the catalogue file itself | `RegulatorySource` | 1 |
| distinct `obligation` (per domain) | `Obligation` | 9 |
| distinct `risk` (per domain) | `Risk` | 9 |
| distinct `control` (per domain) | `Control` + `ControlVersion` | 9 |
| each array entry | `ControlTest` + `ControlTestVersion` | 54 |
| `data_sources` × `required_data_fields` | `EvidenceRequirement` | 1 per test |
| distinct `remediation_template` (per domain) | `RemediationTemplate` | 9 |
| (constant) `applicability_notes` | `ApplicabilityRule` | 9 (1/obligation) |
| every created record | `CatalogueImportRecord` | 1 per record |

Control ↔ Risk links: one per control, to its own domain's risk, `is_primary =
true`. The catalogue expresses no cross-domain control sharing, so the importer
creates none — inferring shared controls from name similarity would be
invention.

---

## 2. Field-by-field mapping

Format: **source field → target field → transformation → assumptions →
validation rule**.

### `control_test_id` → `ControlTest.test_code`

- **Transformation** — verbatim, uppercased and trimmed (e.g. `FAT-001`).
- **Assumptions** — stable across catalogue releases; it is the natural key
  used for idempotent upsert.
- **Validation** — must be non-empty, unique within the file, and match
  `^[A-Z]{3}-\d{3}$`. A duplicate id aborts the import (it would make
  idempotency ambiguous).

### `domain` → `Control.domain`, and `ControlTest` grouping

- **Transformation** — verbatim.
- **Assumptions** — domain is the grouping key for control/obligation/risk;
  verified 1:1:1 above.
- **Validation** — non-empty; every entry in a domain must agree on
  `obligation`, `risk` and `control`. Disagreement is reported as an error, not
  silently resolved by picking the first.

### `control` → `ControlVersion.name`; derived `Control.control_code`

- **Transformation** — `name` verbatim. `control_code` is derived as
  `CTL-<prefix>` from the test-id prefix (e.g. `CTL-FAT`), *not* from the
  control text, so it stays stable if wording is edited.
- **Assumptions** — the test-id prefix is a reliable domain key (verified: one
  prefix per domain, no prefix shared across domains).
- **Validation** — exactly one prefix per domain; a domain with two prefixes is
  an error.

### `control` → `ControlVersion.objective`

- **Transformation** — the source has no separate objective field. The control
  name is carried into `objective` **prefixed with a marker** noting it was not
  separately stated, rather than fabricating an objective sentence.
- **Assumptions** — none. This is a known gap.
- **Validation** — flagged `NEEDS_REVIEW` reason `objective_not_in_source`.

### `obligation` → `Obligation.name` / `Obligation.description`

- **Transformation** — the source string is a single sentence used for both;
  `obligation_code` derived as `OBL-<prefix>`.
- **Assumptions** — the sentence is the duty as an operator should read it.
- **Validation** — non-empty; consistent within domain.

### `risk` → `Risk.name` / `Risk.description`

- **Transformation** — as for obligation; `risk_code` = `RSK-<prefix>`.
- **Assumptions** — describes the unsafe outcome, not the control failure.
- **Validation** — non-empty; consistent within domain.

### `name` → `ControlTestVersion.name`

- **Transformation** — verbatim.
- **Validation** — non-empty.

### `test_logic` → `ControlTestVersion.test_logic_description` **and** `rule_configuration.source_test_logic`

- **Transformation** — stored verbatim in the human-readable description, and
  again inside `rule_configuration` so the rule's origin travels with it:

  ```json
  {
    "kind": "UNSPECIFIED",
    "needs_review": true,
    "review_reasons": ["no_executable_rule_in_source"],
    "source_test_logic": "Calculate actual work time against configured effective-dated fatigue rule pack."
  }
  ```

- **Assumptions** — **none, deliberately.** No threshold, window, operator or
  rule-pack binding is inferred. See §0.2.
- **Validation** — the importer asserts the produced configuration contains no
  numeric literal that did not appear in the source. A test enforces this
  (`test_importer_never_invents_a_threshold`).

### `test_type` → `ControlTestVersion.test_type`

- **Transformation** — case-insensitive lookup:

  | Source | Target | Note |
  |---|---|---|
  | `Deterministic` (35) | `DETERMINISTIC` | |
  | `Analytical` (15) | `ANALYTICAL` | |
  | `AI` (2) | `AI_ASSISTED` | |
  | `Rule` (2) | `DETERMINISTIC` | **flagged** — see below |

- **Assumptions** — `Rule` is a labelling inconsistency, not a fifth execution
  model: `FAT-006` and `FAT-007` do the same kind of status/expiry check as
  entries labelled `Deterministic` (already recorded in `docs/DECISIONS.md`
  §1.2). Normalised to `DETERMINISTIC` and flagged `NEEDS_REVIEW` reason
  `test_type_rule_normalised`, so the assumption is visible rather than buried.
- **Validation** — an unrecognised value is an error, never a silent default.
  `MANUAL` never appears in the source; the importer does not synthesise it.

### `human_review_required` → `ControlTestVersion.human_review_required`

- **Transformation** — boolean verbatim, **except** that `AI_ASSISTED` tests
  are forced to `true` regardless of source.
- **Assumptions** — AI output can never be a final compliance determination
  (CLAUDE.md principles 1–3). The source already sets `true` for both AI
  entries, so the override changes nothing today; it exists so a future
  catalogue revision cannot weaken the invariant by data alone.
- **Validation** — if an `AI_ASSISTED` entry arrives with `false`, the importer
  overrides it *and* records a validation warning.

### `psoe_dimension` → `ControlTestVersion.psoe_impact`, `ControlVersion.psoe_relevance`

- **Transformation** — split on `/`, upper-case, map to `PsoeDimension`.
  `"Operating/Effective"` → `["OPERATING", "EFFECTIVE"]`. A control's
  `psoe_relevance` is the **union** across its tests.
- **Assumptions** — `/` is a separator, not a "one of these" ambiguity.
- **Validation** — every token must resolve to a `PsoeDimension`; an unknown
  token is an error. Empty result is an error.

### `default_severity` → `ControlTestVersion.severity_configuration`

- **Transformation** — `"High"` → `{"default": "HIGH"}`.
- **Assumptions** — the source states a flat default only. **No escalation
  rules are synthesised** — the hand-written sample seed has escalations, but
  those are illustrative and must not be projected onto imported entries.
- **Validation** — must be one of `LOW|MEDIUM|HIGH|CRITICAL` (source uses
  Medium/High/Critical). Unknown severity is an error.

### `evidence` + `data_sources` + `required_data_fields` → `EvidenceRequirement`

- **Transformation** — one `EvidenceRequirement` per test:
  - `name` ← `evidence` string (comma-joined prose, e.g. `"EWD/work diary,
    roster, trip schedule, training, override record"`), truncated to column
    width;
  - `required_fields` ← `required_data_fields` verbatim;
  - `source_type` ← **first** `data_sources` entry mapped through the table
    below; the full list is preserved in the description.
- **Assumptions** — the catalogue lists several source systems per test but
  gives no per-field attribution, so it is not possible to say which field
  comes from which system. Collapsing to one `source_type` loses information;
  the full list is therefore kept in `description` and flagged.
- **Validation** — `required_data_fields` must be non-empty; flagged
  `NEEDS_REVIEW` reason `evidence_source_attribution_unresolved` whenever more
  than one data source is listed (applies to all 54 entries).

  Data-source vocabulary mapping:

  | Source token | `EvidenceSourceType` |
  |---|---|
  | `TMS` | `TMS` |
  | `EWD` | `EWD` |
  | `Telematics` | `TELEMATICS` |
  | `Fleet maintenance`, `Maintenance` | `FLEET_MAINTENANCE` |
  | `HR`, `LMS`, `HR/LMS` | `HR_LMS` |
  | `WMS` | `WMS` |
  | `Weighbridge` | `WEIGHBRIDGE` |
  | `Permit register` | `PERMIT_REGISTER` |
  | `Driver app` | `DRIVER_APP` |
  | `Incident system` | `INCIDENT_SYSTEM` |
  | `Supplier portal`, `Procurement/ERP`, `Contract system`, `Assurance platform` | `SUPPLIER_PORTAL` |
  | `DMS`, `Email/DMS`, `GRC`, `Vehicle master`, `Customer portal` | `DOCUMENT` |

  Tokens in the last two rows are lossy generalisations and are individually
  flagged `data_source_generalised`.

### `remediation_template` → `RemediationTemplate`

- **Transformation** — one per domain (9 distinct values). The source is a
  semicolon-joined sentence; split on `;` into `suggested_steps`, with the
  whole string kept in `description`. `template_code` = `REM-<prefix>`.
- **Assumptions** — `;` separates discrete actions. `default_owner_type`,
  `default_due_days`, `requires_closure_evidence` and
  `requires_effectiveness_check` **are not in the source** and are not
  inferred from severity; the model defaults apply and the record is flagged.
- **Validation** — flagged `NEEDS_REVIEW` reason
  `remediation_defaults_not_in_source`.

### `applicability_notes` → `ApplicabilityRule`

- **Transformation** — one rule per obligation, `criteria = {}` (empty), the
  boilerplate sentence in `description`, `rule_code` = `APP-<prefix>`.
- **Assumptions** — **none.** The sentence names the *dimensions* that decide
  applicability but supplies no values, so no jurisdiction list, CoR role list
  or accreditation condition can be derived. An empty `criteria` means "does
  not constrain" in the evaluator, which is the safe reading for a duty.
- **Validation** — always flagged `NEEDS_REVIEW` reason
  `applicability_criteria_not_in_source`.

### `regulation_layer` → `Regulation` attribution

- **Transformation** — all obligations attributed to the `HVNL` regulation. The
  raw string is preserved in `source_reference` and in provenance.
- **Assumptions** — CoR is part of the HVNL, so it needs no separate
  regulation. HVA is deliberately **excluded** (§0.3).
- **Validation** — flagged `NEEDS_REVIEW` reason
  `regulation_layer_compound_hvnl_cor_hva`.

### `finding_template` → *(no target)*

- **Transformation** — preserved in provenance only.
- **Assumptions** — `Finding` is a runtime record produced by evaluation, not
  graph reference data. There is no graph entity to receive this, and creating
  one to hold a template string would be premature.
- **Validation** — none; recorded so nothing is silently dropped.

### `product_phase` → *(no target)*

- **Transformation** — preserved in provenance only (`P1` ×47, `P2` ×7).
- **Assumptions** — delivery sequencing is roadmap metadata, not regulatory
  content; it does not belong in an effective-dated graph.
- **Validation** — none.

---

## 3. Fields the target requires that the source does not supply

These are **not** invented. Each is set to an explicit placeholder and flagged.

| Target field | Why it cannot be derived | Importer behaviour |
|---|---|---|
| `ControlVersion.owner_type` | No owner in source | `COMPLIANCE_MANAGER` placeholder + `control_owner_not_in_source` |
| `ControlVersion.frequency` | No frequency in source | `EVENT_DRIVEN` placeholder + `control_frequency_not_in_source` |
| `ControlVersion.automation_level` | Not stated | Derived only where unambiguous: all-`MANUAL` tests → `MANUAL`, otherwise `SEMI_AUTOMATED` + flag |
| `ControlTestVersion.rule_configuration` | §0.2 | `kind: UNSPECIFIED` + `no_executable_rule_in_source` |
| `ApplicabilityRule.criteria` | §0.3 | `{}` + `applicability_criteria_not_in_source` |
| `effective_from` / `effective_to` | **No dates anywhere in the source** | Supplied as an explicit importer parameter; the catalogue `date` (2026-08-18) is the default and is recorded as its origin. Never guessed per-entry. |
| `RiskLikelihood` / `RiskConsequence` | Not rated in source | Left `NULL`. Not inferred from severity — test severity and inherent risk rating are different judgements. |
| `reviewed_by` / `approved_by` | Nobody has reviewed an import | `NULL` unless explicitly supplied (see §5) |

---

## 4. Idempotency

Re-running the importer over the same file must not duplicate anything.

- **Natural keys** — every entity is upserted on a deterministic code derived
  from the source (`test_code`, `control_code`, `obligation_code`, `risk_code`,
  `requirement_code`, `template_code`, `rule_code`), never on a random UUID.
- **Version preservation** — an existing record whose content is **unchanged**
  is left completely untouched (no new version, no `updated_at` churn). Where
  content *has* changed:
  - if the current version is still editable (`DRAFT` / `IN_REVIEW` /
    `APPROVED`), it is updated in place;
  - if it is published (`ACTIVE` / `SUPERSEDED` / `RETIRED`), it is **never**
    mutated — a new version is created and the previous one superseded through
    `app/services/versioning.py`, preserving the historical record.
- **Provenance rows** are upserted on
  `(source_file, source_entity_id, target_table)`, so re-import updates the
  existing row rather than appending.

`tests/test_catalogue_importer.py` proves this by importing twice and asserting
identical counts and identical primary keys.

---

## 5. Lifecycle status of imported content

Imported records default to **`DRAFT`**. Nothing in this catalogue has been
through compliance review inside this system, so nothing should be presented as
in force by default, and the governance gate in `services/versioning.py`
already refuses to activate a version without a recorded reviewer and approver.

The development seed passes an explicit status and reviewer/approver so the
Control Explorer has content to display. That represents **development fixture
activation, not genuine compliance review**, and the script says so. The real
safety property is unaffected either way: every imported
`rule_configuration` remains `kind: UNSPECIFIED`, so no imported test can
execute regardless of its lifecycle status.

---

## 6. Provenance

Every created or updated record gets a `CatalogueImportRecord` row
(`catalogue_import_records`) capturing:

- `source_file`, `source_version` (`2.0`), `source_checksum` (SHA-256 of the
  file as imported), `source_entity_id` (e.g. `FAT-001`, or
  `DOMAIN:Fatigue / Work-Rest` for domain-derived records);
- `target_table` and `target_id`;
- `needs_review` and `review_reasons` (the flags named throughout this
  document);
- `source_payload` — the original JSON entry, so a reviewer can compare the
  imported record against exactly what was read;
- `imported_at`.

In addition, each versioned record's `source_reference` carries a human-readable
citation, e.g.
`Logistics_Compliance_Control_Test_Catalogue_v2.json#FAT-001 (catalogue v2.0, 2026-08-18)`.

The checksum matters: if the file changes, the recorded checksum no longer
matches, and a reviewer can tell that imported content derives from a different
revision than the one on disk.

---

## 7. Expected review load

Every one of the 54 imported tests carries at least
`no_executable_rule_in_source`; every obligation carries
`applicability_criteria_not_in_source`. This is the honest outcome: **the
catalogue is a specification of what to test, not a definition of how.** The
import gives the graph its structure and provenance; a compliance specialist
must still supply every threshold before a single test can run.
