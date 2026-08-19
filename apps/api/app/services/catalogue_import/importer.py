"""Import a control-test catalogue into the Compliance Control Graph.

Design commitments, each traceable to docs/CONTROL_IMPORT_MAPPING.md:

  * **Nothing is invented.** Where the source has no value — thresholds,
    applicability criteria, control owner, frequency, risk rating — the
    importer writes an explicit placeholder and records a review reason. It
    never derives a number that did not appear in the source.
  * **Idempotent.** Every record is upserted on a deterministic code derived
    from the source. Re-importing an unchanged file changes nothing at all.
  * **Versions are preserved.** Published versions are never mutated; a changed
    payload creates a new version and supersedes the old one through
    `services.versioning`.
  * **Errors surface.** Validation runs first and aborts the whole import; no
    partial graph is left behind.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.graph_enums import (
    AutomationLevel,
    ControlFrequency,
    ControlOwnerType,
    LifecycleStatus,
    TestType,
)
from app.models import (
    ApplicabilityRule,
    CatalogueImportRecord,
    Control,
    ControlRiskLink,
    ControlTest,
    ControlTestVersion,
    ControlVersion,
    EvidenceRequirement,
    Obligation,
    Regulation,
    RegulationVersion,
    RegulatorySource,
    RemediationTemplate,
    Risk,
)
from app.services import versioning
from app.services.catalogue_import import parsing, vocabulary as vocab
from app.services.catalogue_import.parsing import SourceCatalogue, ValidationIssue

#: Regulation the catalogue's obligations are attributed to. The source's
#: `regulation_layer` names three frameworks at once ("HVNL / CoR / HVA where
#: applicable"); CoR sits inside the HVNL, and HVA is a *voluntary* scheme that
#: must never be presented as a source of obligation. See mapping doc §0.3.
HVNL_CODE = "HVNL"


class CatalogueImportError(AppError):
    """The catalogue could not be imported."""

    def __init__(self, message: str, issues: list[ValidationIssue] | None = None):
        super().__init__(code="catalogue_import_failed", message=message, status_code=422)
        self.issues = issues or []


@dataclass
class ImportReport:
    """What an import did. Printed by the CLI and asserted on by tests."""

    source_file: str
    source_version: str
    checksum: str
    created: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)
    unchanged: dict[str, int] = field(default_factory=dict)
    new_versions: dict[str, int] = field(default_factory=dict)
    warnings: list[ValidationIssue] = field(default_factory=list)
    needs_review: int = 0
    review_reason_counts: dict[str, int] = field(default_factory=dict)

    def _bump(self, bucket: dict[str, int], table: str) -> None:
        bucket[table] = bucket.get(table, 0) + 1

    @property
    def total_created(self) -> int:
        return sum(self.created.values())

    @property
    def total_updated(self) -> int:
        return sum(self.updated.values())


class CatalogueImporter:
    def __init__(
        self,
        db: Session,
        catalogue: SourceCatalogue,
        *,
        effective_from: date,
        status: LifecycleStatus = LifecycleStatus.DRAFT,
        reviewed_by_id: uuid.UUID | None = None,
        approved_by_id: uuid.UUID | None = None,
    ) -> None:
        """
        `effective_from` is required and has no default derived from "today":
        the catalogue contains no dates, so the caller must state when this
        content takes effect rather than have the importer guess.

        `status` defaults to DRAFT because nothing imported has been reviewed
        inside this system. Activating requires a reviewer and an approver,
        enforced below and in `services.versioning`.
        """
        self.db = db
        self.catalogue = catalogue
        self.effective_from = effective_from
        self.status = status
        self.reviewed_by_id = reviewed_by_id
        self.approved_by_id = approved_by_id
        self.report = ImportReport(
            source_file=catalogue.file_name,
            source_version=catalogue.version,
            checksum=catalogue.checksum,
            warnings=list(catalogue.warnings),
        )

    # --- entry point ------------------------------------------------------

    def run(self) -> ImportReport:
        if self.catalogue.fatal_issues:
            raise CatalogueImportError(
                f"Catalogue failed validation with {len(self.catalogue.fatal_issues)} "
                f"error(s); nothing was imported.",
                self.catalogue.fatal_issues,
            )

        if self.status is LifecycleStatus.ACTIVE and (
            self.reviewed_by_id is None or self.approved_by_id is None
        ):
            raise CatalogueImportError(
                "Importing as ACTIVE requires a reviewer and an approver: regulatory "
                "content cannot become binding without a recorded review trail."
            )

        self._version_kwargs = {
            "status": self.status,
            "reviewed_by_id": self.reviewed_by_id,
            "approved_by_id": self.approved_by_id,
        }

        source = self._upsert_regulatory_source()
        regulation = self._upsert_regulation(source)

        for domain, entries in sorted(self.catalogue.entries_by_domain().items()):
            self._import_domain(domain, entries, regulation)

        self.db.flush()
        return self.report

    # --- provenance -------------------------------------------------------

    def _record_provenance(
        self,
        *,
        entity_id: str,
        target_table: str,
        target_id: uuid.UUID | None,
        payload: dict,
        review_reasons: list[str],
    ) -> None:
        needs_review = bool(review_reasons)
        existing = self.db.execute(
            select(CatalogueImportRecord).where(
                CatalogueImportRecord.source_file == self.catalogue.file_name,
                CatalogueImportRecord.source_entity_id == entity_id,
                CatalogueImportRecord.target_table == target_table,
            )
        ).scalar_one_or_none()

        if existing is None:
            self.db.add(
                CatalogueImportRecord(
                    source_file=self.catalogue.file_name,
                    source_version=self.catalogue.version,
                    source_checksum=self.catalogue.checksum,
                    source_entity_id=entity_id,
                    target_table=target_table,
                    target_id=target_id,
                    needs_review=needs_review,
                    review_reasons=review_reasons,
                    source_payload=payload,
                )
            )
        else:
            # Re-import updates the row in place — provenance must not accumulate
            # duplicates for the same source entity.
            existing.source_version = self.catalogue.version
            existing.source_checksum = self.catalogue.checksum
            existing.target_id = target_id
            existing.needs_review = needs_review
            existing.review_reasons = review_reasons
            existing.source_payload = payload

        if needs_review:
            self.report.needs_review += 1
            for reason in review_reasons:
                self.report.review_reason_counts[reason] = (
                    self.report.review_reason_counts.get(reason, 0) + 1
                )

    # --- regulation -------------------------------------------------------

    def _upsert_regulatory_source(self) -> RegulatorySource:
        code = f"CATALOGUE-{self.catalogue.version}"
        source = self.db.execute(
            select(RegulatorySource).where(RegulatorySource.source_code == code)
        ).scalar_one_or_none()

        if source is None:
            source = RegulatorySource(
                source_code=code,
                name=f"Logistics Compliance Control Test Catalogue v{self.catalogue.version}",
                publisher="Logistics Compliance Intelligence Platform",
                document_type="Control test catalogue",
                notes=(
                    f"Imported from {self.catalogue.file_name}; "
                    f"SHA-256 {self.catalogue.checksum}"
                ),
            )
            self.db.add(source)
            self.db.flush()
            self.report._bump(self.report.created, "regulatory_sources")
        else:
            self.report._bump(self.report.unchanged, "regulatory_sources")
        return source

    def _upsert_regulation(self, source: RegulatorySource) -> Regulation:
        regulation = self.db.execute(
            select(Regulation).where(Regulation.regulation_code == HVNL_CODE)
        ).scalar_one_or_none()

        if regulation is None:
            regulation = Regulation(
                regulation_code=HVNL_CODE,
                name="Heavy Vehicle National Law",
                short_name="HVNL",
                regulator="National Heavy Vehicle Regulator",
            )
            self.db.add(regulation)
            self.db.flush()
            self.report._bump(self.report.created, "regulations")

            self.db.add(
                RegulationVersion(
                    regulation_id=regulation.id,
                    regulatory_source_id=source.id,
                    version=1,
                    effective_from=self.effective_from,
                    source_reference=self.catalogue.citation("regulation_layer"),
                    title="Heavy Vehicle National Law",
                    summary=(
                        "Attributed from the control catalogue's regulation_layer field. "
                        "Chain of Responsibility duties sit within this law; Heavy Vehicle "
                        "Accreditation is a separate voluntary scheme and is deliberately "
                        "not modelled as a source of obligation."
                    ),
                    # Jurisdictions are not stated in the catalogue, so none are
                    # asserted here rather than assuming the HVNL participant set.
                    jurisdiction_codes=[],
                    **self._version_kwargs,
                )
            )
            self.report._bump(self.report.created, "regulation_versions")
        else:
            self.report._bump(self.report.unchanged, "regulations")

        self._record_provenance(
            entity_id="regulation_layer",
            target_table="regulations",
            target_id=regulation.id,
            payload={"regulation_layer": self.catalogue.entries[0].get("regulation_layer")},
            review_reasons=[vocab.REGULATION_LAYER_COMPOUND],
        )
        return regulation

    # --- per-domain -------------------------------------------------------

    def _import_domain(self, domain: str, entries: list[dict], regulation: Regulation) -> None:
        prefix = vocab.code_prefix(entries[0]["control_test_id"])
        first = entries[0]
        domain_key = f"DOMAIN:{domain}"

        obligation = self._upsert_obligation(prefix, first, regulation, domain_key)
        self._upsert_applicability_rule(prefix, first, obligation, domain_key)
        risk = self._upsert_risk(prefix, first, obligation, domain_key)
        control, control_version = self._upsert_control(prefix, domain, entries, domain_key)
        self._link_control_to_risk(control, risk)

        for entry in entries:
            self._import_test(entry, control, control_version)

    def _upsert_obligation(
        self, prefix: str, entry: dict, regulation: Regulation, domain_key: str
    ) -> Obligation:
        code = f"OBL-{prefix}"
        text = entry["obligation"].strip()

        obligation = self._current(Obligation, Obligation.obligation_code, code)
        payload = {
            "name": text,
            "description": text,
            "regulation_id": regulation.id,
            # CoR roles are not stated per obligation in the source; the only
            # applicability text is generic boilerplate. Asserting roles here
            # would be invention.
            "cor_role_codes": [],
        }

        obligation = self._upsert_versioned(
            Obligation,
            Obligation.obligation_code,
            code,
            payload,
            source_reference=self.catalogue.citation(domain_key),
            table="obligations",
            identity={"obligation_code": code},
        )

        self._record_provenance(
            entity_id=domain_key,
            target_table="obligations",
            target_id=obligation.id,
            payload={"obligation": text, "regulation_layer": entry.get("regulation_layer")},
            review_reasons=[vocab.REGULATION_LAYER_COMPOUND],
        )
        return obligation

    def _upsert_applicability_rule(
        self, prefix: str, entry: dict, obligation: Obligation, domain_key: str
    ) -> ApplicabilityRule:
        code = f"APP-{prefix}"
        notes = str(entry.get("applicability_notes", "")).strip()

        rule = self._upsert_versioned(
            ApplicabilityRule,
            ApplicabilityRule.rule_code,
            code,
            {
                "name": f"Applicability for {obligation.name[:80]}",
                "description": notes,
                "obligation_id": obligation.id,
                # The source names the *dimensions* that decide applicability
                # but supplies no values. An empty criteria object means "does
                # not constrain"; inventing a jurisdiction or role list here
                # would silently narrow or widen a legal duty.
                "criteria": {},
            },
            source_reference=self.catalogue.citation(domain_key),
            table="applicability_rules",
            identity={"rule_code": code},
        )

        self._record_provenance(
            entity_id=domain_key,
            target_table="applicability_rules",
            target_id=rule.id,
            payload={"applicability_notes": notes},
            review_reasons=[vocab.APPLICABILITY_NOT_IN_SOURCE],
        )
        return rule

    def _upsert_risk(
        self, prefix: str, entry: dict, obligation: Obligation, domain_key: str
    ) -> Risk:
        code = f"RSK-{prefix}"
        text = entry["risk"].strip()

        risk = self._upsert_versioned(
            Risk,
            Risk.risk_code,
            code,
            {
                "name": text,
                "description": text,
                "obligation_id": obligation.id,
                # Not rated in the source. Deriving a likelihood/consequence
                # from test severity would conflate two different judgements.
                "inherent_likelihood": None,
                "inherent_consequence": None,
            },
            source_reference=self.catalogue.citation(domain_key),
            table="risks",
            identity={"risk_code": code},
        )

        self._record_provenance(
            entity_id=domain_key,
            target_table="risks",
            target_id=risk.id,
            payload={"risk": text},
            review_reasons=[vocab.RISK_RATING_NOT_IN_SOURCE],
        )
        return risk

    def _upsert_control(
        self, prefix: str, domain: str, entries: list[dict], domain_key: str
    ) -> tuple[Control, ControlVersion]:
        code = f"CTL-{prefix}"
        name = entries[0]["control"].strip()

        control = self.db.execute(
            select(Control).where(Control.control_code == code)
        ).scalar_one_or_none()
        if control is None:
            control = Control(control_code=code, domain=domain)
            self.db.add(control)
            self.db.flush()
            self.report._bump(self.report.created, "controls")
        else:
            if control.domain != domain:
                control.domain = domain
                self.report._bump(self.report.updated, "controls")
            else:
                self.report._bump(self.report.unchanged, "controls")

        # PSOE relevance for a control is the union across its tests.
        psoe: list[str] = []
        for entry in entries:
            for dimension in parsing.parse_psoe(entry["psoe_dimension"]):
                if dimension.value not in psoe:
                    psoe.append(dimension.value)

        test_types = {parsing.parse_test_type(e["test_type"])[0] for e in entries}
        automation = (
            AutomationLevel.MANUAL
            if test_types == {TestType.MANUAL}
            else AutomationLevel.SEMI_AUTOMATED
        )

        version = self._upsert_child_version(
            ControlVersion,
            ControlVersion.control_id,
            control.id,
            {
                "name": name,
                # The source has no objective field. Marked rather than
                # fabricated into a plausible-sounding sentence.
                "objective": f"[Objective not stated in source catalogue] {name}",
                "owner_type": ControlOwnerType.COMPLIANCE_MANAGER,
                "frequency": ControlFrequency.EVENT_DRIVEN,
                "automation_level": automation,
                "psoe_relevance": psoe,
            },
            source_reference=self.catalogue.citation(domain_key),
            table="control_versions",
        )

        self._record_provenance(
            entity_id=domain_key,
            target_table="controls",
            target_id=control.id,
            payload={"control": name, "domain": domain},
            review_reasons=[
                vocab.OBJECTIVE_NOT_IN_SOURCE,
                vocab.CONTROL_OWNER_NOT_IN_SOURCE,
                vocab.CONTROL_FREQUENCY_NOT_IN_SOURCE,
                vocab.CONTROL_AUTOMATION_INFERRED,
            ],
        )
        return control, version

    def _link_control_to_risk(self, control: Control, risk: Risk) -> None:
        existing = self.db.execute(
            select(ControlRiskLink).where(
                ControlRiskLink.control_id == control.id,
                ControlRiskLink.risk_id == risk.id,
            )
        ).scalar_one_or_none()
        if existing is None:
            self.db.add(
                ControlRiskLink(control_id=control.id, risk_id=risk.id, is_primary=True)
            )
            self.db.flush()
            self.report._bump(self.report.created, "control_risk_links")
        else:
            self.report._bump(self.report.unchanged, "control_risk_links")

    # --- per-test ---------------------------------------------------------

    def _import_test(
        self, entry: dict, control: Control, control_version: ControlVersion
    ) -> None:
        test_code = entry["control_test_id"].strip().upper()
        reasons: list[str] = [vocab.NO_EXECUTABLE_RULE]

        test_type, normalised = parsing.parse_test_type(entry["test_type"])
        if normalised:
            reasons.append(vocab.TEST_TYPE_RULE_NORMALISED)

        human_review = bool(entry.get("human_review_required", True))
        if test_type is TestType.AI_ASSISTED and not human_review:
            # AI output can never be a final compliance determination.
            human_review = True
            reasons.append(vocab.AI_REVIEW_OVERRIDDEN)

        test = self.db.execute(
            select(ControlTest).where(ControlTest.test_code == test_code)
        ).scalar_one_or_none()
        if test is None:
            test = ControlTest(test_code=test_code, control_id=control.id)
            self.db.add(test)
            self.db.flush()
            self.report._bump(self.report.created, "control_tests")
        else:
            if test.control_id != control.id:
                test.control_id = control.id
                self.report._bump(self.report.updated, "control_tests")
            else:
                self.report._bump(self.report.unchanged, "control_tests")

        version = self._upsert_child_version(
            ControlTestVersion,
            ControlTestVersion.control_test_id,
            test.id,
            {
                "name": entry["name"].strip(),
                "test_logic_description": entry["test_logic"].strip(),
                "test_type": test_type,
                # The catalogue states no thresholds, windows or operators
                # anywhere (see mapping doc §0.2). UNSPECIFIED is not a kind the
                # engine dispatches on, so this test cannot execute until a
                # specialist defines it — which is the correct outcome.
                "rule_configuration": {
                    "kind": "UNSPECIFIED",
                    "needs_review": True,
                    "review_reasons": [vocab.NO_EXECUTABLE_RULE],
                    "source_test_logic": entry["test_logic"].strip(),
                },
                # The source states a flat default only; no escalation bands
                # are synthesised.
                "severity_configuration": {
                    "default": parsing.parse_severity(entry["default_severity"])
                },
                "human_review_required": human_review,
                "psoe_impact": [d.value for d in parsing.parse_psoe(entry["psoe_dimension"])],
            },
            source_reference=self.catalogue.citation(test_code),
            table="control_test_versions",
        )

        evidence_reasons = self._import_evidence(entry, version, test_code)
        self._import_remediation(entry, version, test_code)

        self._record_provenance(
            entity_id=test_code,
            target_table="control_tests",
            target_id=test.id,
            payload=entry,
            review_reasons=reasons + evidence_reasons,
        )

    def _import_evidence(
        self, entry: dict, version: ControlTestVersion, test_code: str
    ) -> list[str]:
        reasons: list[str] = []
        data_sources = [str(s).strip() for s in entry.get("data_sources", [])]

        if len(data_sources) > 1:
            # The catalogue lists several systems but never says which field
            # comes from which, so collapsing to one source_type loses
            # information. The full list is kept in the description.
            reasons.append(vocab.EVIDENCE_ATTRIBUTION_UNRESOLVED)
        if any(s.lower() in vocab.GENERALISED_DATA_SOURCES for s in data_sources):
            reasons.append(vocab.DATA_SOURCE_GENERALISED)

        source_type = vocab.EVIDENCE_SOURCES[data_sources[0].lower()]
        evidence_text = str(entry.get("evidence", "")).strip()

        code = f"EVR-{test_code}"
        self._upsert_versioned(
            EvidenceRequirement,
            EvidenceRequirement.requirement_code,
            code,
            {
                # The parent link is content, not identity: when the test
                # version supersedes, this points at the new one while the
                # previous requirement row stays attached to the previous test
                # version, keeping a historical result reproducible.
                "control_test_version_id": version.id,
                "name": evidence_text[:500] or f"Evidence for {test_code}",
                "description": (
                    f"Source systems listed in catalogue: {', '.join(data_sources)}. "
                    f"Per-field attribution is not stated in the source."
                ),
                "source_type": source_type,
                "required_fields": list(entry.get("required_data_fields", [])),
                # Mandatory by default: a test that cannot see its evidence is
                # not assessable, which must never be reported as a pass.
                "is_mandatory": True,
                # Freshness is not stated in the source, so none is asserted.
                "max_age_days": None,
            },
            source_reference=self.catalogue.citation(test_code),
            table="evidence_requirements",
            identity={"requirement_code": code},
        )
        return reasons

    def _import_remediation(
        self, entry: dict, version: ControlTestVersion, test_code: str
    ) -> None:
        text = str(entry.get("remediation_template", "")).strip()
        code = f"REM-{test_code}"

        self._upsert_versioned(
            RemediationTemplate,
            RemediationTemplate.template_code,
            code,
            {
                "control_test_version_id": version.id,
                "title": entry["finding_template"].strip()
                if entry.get("finding_template")
                else f"Remediation for {test_code}",
                "description": text,
                "suggested_steps": parsing.parse_remediation_steps(text),
                # Owner, due window and closure requirements are not in the
                # source; model defaults apply and the record is flagged.
                "default_owner_type": ControlOwnerType.COMPLIANCE_MANAGER,
                "default_due_days": 14,
                "requires_closure_evidence": True,
                "requires_effectiveness_check": False,
            },
            source_reference=self.catalogue.citation(test_code),
            table="remediation_templates",
            identity={"template_code": code},
        )

        self._record_provenance(
            entity_id=test_code,
            target_table="remediation_templates",
            target_id=None,
            payload={"remediation_template": text},
            review_reasons=[vocab.REMEDIATION_DEFAULTS_NOT_IN_SOURCE],
        )

    # --- upsert machinery -------------------------------------------------

    def _current(self, model, code_column, code):
        rows = self.db.execute(select(model).where(code_column == code)).scalars().all()
        return max(rows, key=lambda r: r.version) if rows else None

    def _payload_matches(self, record, payload: dict) -> bool:
        return all(getattr(record, key) == value for key, value in payload.items())

    def _apply(self, record, payload: dict, source_reference: str) -> None:
        for key, value in payload.items():
            setattr(record, key, value)
        record.source_reference = source_reference

    def _upsert_versioned(
        self,
        model,
        code_column,
        code: str,
        payload: dict,
        *,
        source_reference: str,
        table: str,
        identity: dict,
    ):
        """Upsert an in-place-versioned record keyed on its code."""
        existing = self._current(model, code_column, code)

        if existing is None:
            record = model(
                **identity,
                **payload,
                version=1,
                effective_from=self.effective_from,
                source_reference=source_reference,
                **self._version_kwargs,
            )
            self.db.add(record)
            self.db.flush()
            self.report._bump(self.report.created, table)
            return record

        if self._payload_matches(existing, payload) and existing.source_reference == source_reference:
            # Genuinely unchanged: touch nothing, so a repeat import is a no-op.
            self.report._bump(self.report.unchanged, table)
            return existing

        return self._revise(existing, model, payload, source_reference, table, identity)

    def _upsert_child_version(
        self,
        model,
        parent_column,
        parent_id: uuid.UUID,
        payload: dict,
        *,
        source_reference: str,
        table: str,
        match_extra: dict | None = None,
    ):
        """Upsert a version row hanging off a parent container."""
        stmt = select(model).where(parent_column == parent_id)
        for key, value in (match_extra or {}).items():
            stmt = stmt.where(getattr(model, key) == value)
        rows = self.db.execute(stmt).scalars().all()
        existing = max(rows, key=lambda r: r.version) if rows else None

        identity = {parent_column.key: parent_id, **(match_extra or {})}

        if existing is None:
            record = model(
                **identity,
                **payload,
                version=1,
                effective_from=self.effective_from,
                source_reference=source_reference,
                **self._version_kwargs,
            )
            self.db.add(record)
            self.db.flush()
            self.report._bump(self.report.created, table)
            return record

        if self._payload_matches(existing, payload) and existing.source_reference == source_reference:
            self.report._bump(self.report.unchanged, table)
            return existing

        return self._revise(existing, model, payload, source_reference, table, identity)

    def _revise(self, existing, model, payload, source_reference, table, identity):
        """Content changed. Edit a draft in place; version a published record."""
        if existing.status not in (
            LifecycleStatus.ACTIVE,
            LifecycleStatus.SUPERSEDED,
            LifecycleStatus.RETIRED,
        ):
            self._apply(existing, payload, source_reference)
            self.db.flush()
            self.report._bump(self.report.updated, table)
            return existing

        # Published content is never edited in place — supersede and add a new
        # version so historical assessments stay interpretable.
        if existing.status is LifecycleStatus.ACTIVE:
            if self.effective_from <= existing.effective_from:
                raise CatalogueImportError(
                    f"Cannot supersede {model.__name__} version {existing.version}: the "
                    f"import's effective_from ({self.effective_from}) is not after the "
                    f"active version's ({existing.effective_from}). Pass a later "
                    f"effective_from."
                )
            versioning.supersede(existing, replacement_effective_from=self.effective_from)

        record = model(
            **identity,
            **payload,
            version=existing.version + 1,
            effective_from=self.effective_from,
            source_reference=source_reference,
            **self._version_kwargs,
        )
        self.db.add(record)
        self.db.flush()
        self.report._bump(self.report.new_versions, table)
        return record


def import_catalogue(
    db: Session,
    path: Path,
    *,
    effective_from: date,
    status: LifecycleStatus = LifecycleStatus.DRAFT,
    reviewed_by_id: uuid.UUID | None = None,
    approved_by_id: uuid.UUID | None = None,
) -> ImportReport:
    catalogue = parsing.load_catalogue(path)
    return CatalogueImporter(
        db,
        catalogue,
        effective_from=effective_from,
        status=status,
        reviewed_by_id=reviewed_by_id,
        approved_by_id=approved_by_id,
    ).run()
