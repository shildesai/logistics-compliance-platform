"""Tests for the control-catalogue importer.

The headline requirement is idempotency — repeated imports must not duplicate
controls — but the tests that matter most are the ones proving the importer
does *not* invent regulatory content it was not given.

See docs/CONTROL_IMPORT_MAPPING.md for the mapping these assert against.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.graph_enums import LifecycleStatus, TestType
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
    RemediationTemplate,
    Risk,
)
from app.services.catalogue_import import (
    CatalogueImportError,
    import_catalogue,
    load_catalogue,
)
from app.services.catalogue_import import vocabulary as vocab

CATALOGUE = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "reference"
    / "Logistics_Compliance_Control_Test_Catalogue_v2.json"
)

EFFECTIVE_FROM = date(2026, 8, 18)

#: Counts derived from the source and documented in the mapping: 54 entries
#: collapsing to 9 domains.
EXPECTED_TESTS = 54
EXPECTED_DOMAINS = 9


@pytest.fixture()
def catalogue_path(tmp_path) -> Path:
    """A private copy, so tests that mutate the source cannot corrupt the repo."""
    target = tmp_path / CATALOGUE.name
    target.write_text(CATALOGUE.read_text())
    return target


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload))
    return path


def _counts(db) -> dict[str, int]:
    models = (
        Regulation,
        Obligation,
        Risk,
        Control,
        ControlVersion,
        ControlTest,
        ControlTestVersion,
        EvidenceRequirement,
        RemediationTemplate,
        ApplicabilityRule,
        ControlRiskLink,
        CatalogueImportRecord,
    )
    return {
        m.__name__: db.execute(select(func.count()).select_from(m)).scalar_one()
        for m in models
    }


# --- Shape ----------------------------------------------------------------


def test_import_produces_the_documented_shape(db, clean_graph, catalogue_path):
    """54 source entries become 54 tests but only 9 controls — the entries are
    control *tests*, and importing each as a control would fragment the graph."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    counts = _counts(db)
    assert counts["ControlTest"] == EXPECTED_TESTS
    assert counts["Control"] == EXPECTED_DOMAINS
    assert counts["Obligation"] == EXPECTED_DOMAINS
    assert counts["Risk"] == EXPECTED_DOMAINS
    assert counts["ApplicabilityRule"] == EXPECTED_DOMAINS


def test_test_codes_match_the_source_exactly(db, clean_graph, catalogue_path):
    """Provenance depends on imported codes being the source's own ids."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    source_ids = {e["control_test_id"] for e in json.loads(catalogue_path.read_text())["controls"]}
    imported = set(db.execute(select(ControlTest.test_code)).scalars().all())
    assert source_ids == imported


def test_every_control_links_to_its_risk(db, clean_graph, catalogue_path):
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    assert _counts(db)["ControlRiskLink"] == EXPECTED_DOMAINS


# --- Idempotency (the headline requirement) -------------------------------


def test_repeated_import_does_not_duplicate_controls(db, clean_graph, catalogue_path):
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    first = _counts(db)

    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    second = _counts(db)

    assert first == second, "a repeated import changed row counts"
    assert second["Control"] == EXPECTED_DOMAINS
    assert second["ControlTest"] == EXPECTED_TESTS


def test_repeated_import_preserves_primary_keys(db, clean_graph, catalogue_path):
    """Stronger than counts: the same rows must survive, not be swapped for
    an equal number of new ones."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    before = sorted(db.execute(select(ControlTest.id)).scalars().all(), key=str)

    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    after = sorted(db.execute(select(ControlTest.id)).scalars().all(), key=str)

    assert before == after


def test_repeated_import_reports_no_work_done(db, clean_graph, catalogue_path):
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    report = import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert report.total_created == 0
    assert report.total_updated == 0
    assert report.new_versions == {}


def test_repeated_import_does_not_bump_versions(db, clean_graph, catalogue_path):
    """An unchanged source must not manufacture version churn."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    versions = db.execute(select(ControlTestVersion.version)).scalars().all()
    assert set(versions) == {1}


def test_repeated_import_does_not_duplicate_provenance(db, clean_graph, catalogue_path):
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    first = _counts(db)["CatalogueImportRecord"]

    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    assert _counts(db)["CatalogueImportRecord"] == first


# --- Version preservation -------------------------------------------------


def test_changed_content_supersedes_a_published_version(db, clean_graph, catalogue_path, two_tenants):
    """Published content is never edited in place; the old version survives so
    a past assessment stays interpretable."""
    reviewer = two_tenants.platform_admin.id
    import_catalogue(
        db,
        catalogue_path,
        effective_from=EFFECTIVE_FROM,
        status=LifecycleStatus.ACTIVE,
        reviewed_by_id=reviewer,
        approved_by_id=reviewer,
    )

    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["name"] = "Work-time threshold exception (revised)"
    _write(catalogue_path, payload)

    import_catalogue(
        db,
        catalogue_path,
        effective_from=date(2027, 1, 1),
        status=LifecycleStatus.ACTIVE,
        reviewed_by_id=reviewer,
        approved_by_id=reviewer,
    )

    test = db.execute(
        select(ControlTest).where(ControlTest.test_code == payload["controls"][0]["control_test_id"])
    ).scalar_one()
    versions = sorted(test.versions, key=lambda v: v.version)

    assert [v.version for v in versions] == [1, 2]
    assert versions[0].status is LifecycleStatus.SUPERSEDED
    assert versions[0].effective_to == date(2027, 1, 1)
    assert versions[1].status is LifecycleStatus.ACTIVE
    assert versions[1].name.endswith("(revised)")
    # And no duplicate ControlTest was created for the same code.
    assert _counts(db)["ControlTest"] == EXPECTED_TESTS


def test_changed_content_edits_a_draft_in_place(db, clean_graph, catalogue_path):
    """Drafts have bound nobody, so they are corrected rather than versioned."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["name"] = "Renamed while still a draft"
    _write(catalogue_path, payload)

    report = import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert report.new_versions == {}
    assert report.updated.get("control_test_versions") == 1
    assert set(db.execute(select(ControlTestVersion.version)).scalars().all()) == {1}


def test_superseding_requires_a_later_effective_date(db, clean_graph, catalogue_path, two_tenants):
    reviewer = two_tenants.platform_admin.id
    import_catalogue(
        db,
        catalogue_path,
        effective_from=EFFECTIVE_FROM,
        status=LifecycleStatus.ACTIVE,
        reviewed_by_id=reviewer,
        approved_by_id=reviewer,
    )

    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["name"] = "Changed"
    _write(catalogue_path, payload)

    with pytest.raises(CatalogueImportError, match="not after"):
        import_catalogue(
            db,
            catalogue_path,
            effective_from=EFFECTIVE_FROM,  # same date as the active version
            status=LifecycleStatus.ACTIVE,
            reviewed_by_id=reviewer,
            approved_by_id=reviewer,
        )


# --- Nothing is invented --------------------------------------------------


def test_importer_never_invents_a_threshold(db, clean_graph, catalogue_path):
    """The catalogue contains no digits in any test_logic (mapping §0.2), so no
    imported rule configuration may contain a numeric literal either."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    source_logic = {
        e["control_test_id"]: e["test_logic"]
        for e in json.loads(catalogue_path.read_text())["controls"]
    }

    for version in db.execute(select(ControlTestVersion)).scalars().all():
        rendered = json.dumps(version.rule_configuration)
        # Strip the verbatim source sentence before looking for numbers, so a
        # digit legitimately present in the source is not counted as invented.
        code = version.control_test.test_code
        rendered = rendered.replace(json.dumps(source_logic[code])[1:-1], "")
        assert not re.search(r"\d", rendered), (
            f"{code} rule_configuration contains a number absent from the source: "
            f"{version.rule_configuration}"
        )


def test_imported_rules_are_not_executable(db, clean_graph, catalogue_path):
    """`UNSPECIFIED` is not a kind the engine dispatches on, so an imported
    test structurally cannot run until a specialist defines it."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    for version in db.execute(select(ControlTestVersion)).scalars().all():
        assert version.rule_configuration["kind"] == "UNSPECIFIED"
        assert version.rule_configuration["needs_review"] is True
        assert version.rule_configuration["source_test_logic"]


def test_severity_carries_no_invented_escalations(db, clean_graph, catalogue_path):
    """The source states a flat default; escalation bands must not appear."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    for version in db.execute(select(ControlTestVersion)).scalars().all():
        assert set(version.severity_configuration) == {"default"}


def test_applicability_criteria_are_empty_not_guessed(db, clean_graph, catalogue_path):
    """The source's applicability note names dimensions but gives no values."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    for rule in db.execute(select(ApplicabilityRule)).scalars().all():
        assert rule.criteria == {}
        assert rule.description


def test_risk_ratings_are_left_unset(db, clean_graph, catalogue_path):
    """Inherent risk rating is a different judgement from test severity and is
    not in the source, so it must not be derived from it."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    for risk in db.execute(select(Risk)).scalars().all():
        assert risk.inherent_likelihood is None
        assert risk.inherent_consequence is None


def test_hva_is_not_imported_as_a_source_of_obligation(db, clean_graph, catalogue_path):
    """`regulation_layer` names HVNL, CoR and HVA together. HVA is voluntary;
    attributing an obligation to it would imply accreditation is mandatory."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    codes = set(db.execute(select(Regulation.regulation_code)).scalars().all())
    assert codes == {"HVNL"}
    assert not any("HVA" in c for c in codes)


def test_no_jurisdictions_are_asserted(db, clean_graph, catalogue_path):
    """The catalogue never names a jurisdiction, so none is claimed."""
    from app.models import RegulationVersion

    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)
    for version in db.execute(select(RegulationVersion)).scalars().all():
        assert version.jurisdiction_codes == []


# --- Safety invariants ----------------------------------------------------


def test_ai_tests_always_require_human_review(db, clean_graph, catalogue_path):
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    ai = (
        db.execute(
            select(ControlTestVersion).where(
                ControlTestVersion.test_type == TestType.AI_ASSISTED
            )
        )
        .scalars()
        .all()
    )
    assert ai, "the catalogue contains AI-typed tests"
    assert all(v.human_review_required for v in ai)


def test_human_review_is_forced_on_even_if_the_source_disables_it(db, clean_graph, catalogue_path):
    """A future catalogue revision must not be able to weaken the invariant
    that AI never makes a final determination."""
    payload = json.loads(catalogue_path.read_text())
    ai_entry = next(e for e in payload["controls"] if e["test_type"] == "AI")
    ai_entry["human_review_required"] = False
    _write(catalogue_path, payload)

    report = import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    version = (
        db.execute(
            select(ControlTestVersion)
            .join(ControlTest)
            .where(ControlTest.test_code == ai_entry["control_test_id"])
        )
        .scalars()
        .one()
    )
    assert version.human_review_required is True
    assert any("human_review_required" in w.field for w in report.warnings)


def test_imported_content_defaults_to_draft(db, clean_graph, catalogue_path):
    """Nothing imported has been reviewed inside this system, so nothing should
    present itself as in force."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    statuses = set(db.execute(select(ControlTestVersion.status)).scalars().all())
    assert statuses == {LifecycleStatus.DRAFT}


def test_activating_an_import_requires_a_review_trail(db, clean_graph, catalogue_path):
    with pytest.raises(CatalogueImportError, match="reviewer and an approver"):
        import_catalogue(
            db, catalogue_path, effective_from=EFFECTIVE_FROM, status=LifecycleStatus.ACTIVE
        )


def test_rule_typed_tests_are_normalised_to_deterministic(db, clean_graph, catalogue_path):
    """`Rule` is a labelling inconsistency, not a fifth execution model — and
    the assumption is flagged rather than silently applied."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    flagged = (
        db.execute(
            select(CatalogueImportRecord).where(
                CatalogueImportRecord.review_reasons.any(vocab.TEST_TYPE_RULE_NORMALISED)
            )
        )
        .scalars()
        .all()
    )
    assert len(flagged) == 2, "the source has two 'Rule'-typed entries"

    for record in flagged:
        version = (
            db.execute(
                select(ControlTestVersion)
                .join(ControlTest)
                .where(ControlTest.test_code == record.source_entity_id)
            )
            .scalars()
            .one()
        )
        assert version.test_type is TestType.DETERMINISTIC


# --- Validation reporting -------------------------------------------------


def test_unknown_test_type_is_rejected_not_defaulted(db, clean_graph, catalogue_path):
    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["test_type"] = "Telepathic"
    _write(catalogue_path, payload)

    with pytest.raises(CatalogueImportError) as exc:
        import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert any("Unknown test type" in i.message for i in exc.value.issues)


def test_unmapped_data_source_is_rejected(db, clean_graph, catalogue_path):
    """A new source system must be added to the vocabulary deliberately, not
    fall through to a generic default."""
    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["data_sources"] = ["Some New System"]
    _write(catalogue_path, payload)

    with pytest.raises(CatalogueImportError) as exc:
        import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert any("Unmapped data source" in i.message for i in exc.value.issues)


def test_duplicate_test_id_is_rejected(db, clean_graph, catalogue_path):
    """Duplicates would make the idempotency key ambiguous."""
    payload = json.loads(catalogue_path.read_text())
    payload["controls"].append(copy.deepcopy(payload["controls"][0]))
    _write(catalogue_path, payload)

    with pytest.raises(CatalogueImportError) as exc:
        import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert any("Duplicate control_test_id" in i.message for i in exc.value.issues)


def test_inconsistent_domain_is_reported_not_silently_resolved(db, clean_graph, catalogue_path):
    """The import collapses a domain into one obligation; disagreement within
    the domain must surface rather than being resolved by taking the first."""
    payload = json.loads(catalogue_path.read_text())
    domain = payload["controls"][0]["domain"]
    second = next(e for e in payload["controls"][1:] if e["domain"] == domain)
    second["obligation"] = "A completely different duty"
    _write(catalogue_path, payload)

    with pytest.raises(CatalogueImportError) as exc:
        import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert any("distinct obligation values" in i.message for i in exc.value.issues)


def test_missing_required_field_is_reported(db, clean_graph, catalogue_path):
    payload = json.loads(catalogue_path.read_text())
    del payload["controls"][0]["risk"]
    _write(catalogue_path, payload)

    with pytest.raises(CatalogueImportError) as exc:
        import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert any(i.field == "risk" for i in exc.value.issues)


def test_a_failed_import_writes_nothing(db, clean_graph, catalogue_path):
    """Validation runs before any write, so a bad catalogue leaves no partial
    graph behind."""
    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["test_type"] = "Nonsense"
    _write(catalogue_path, payload)

    with pytest.raises(CatalogueImportError):
        import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    assert _counts(db)["ControlTest"] == 0
    assert _counts(db)["Control"] == 0


def test_validation_collects_every_problem_at_once(db, clean_graph, catalogue_path):
    """A reviewer should see all errors in one report, not one per re-run."""
    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["test_type"] = "Nonsense"
    payload["controls"][1]["default_severity"] = "Apocalyptic"
    _write(catalogue_path, payload)

    catalogue = load_catalogue(catalogue_path)
    assert len(catalogue.fatal_issues) >= 2


# --- Provenance -----------------------------------------------------------


def test_provenance_records_the_source_identity(db, clean_graph, catalogue_path):
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    record = db.execute(
        select(CatalogueImportRecord).where(
            CatalogueImportRecord.source_entity_id == "FAT-001",
            CatalogueImportRecord.target_table == "control_tests",
        )
    ).scalars().one()

    assert record is not None
    assert record.source_file.endswith(".json")
    assert record.source_version == "2.0"
    assert len(record.source_checksum) == 64
    # The original entry is kept so a reviewer can compare against what was read.
    assert record.source_payload["control_test_id"] == "FAT-001"
    assert record.source_payload["test_logic"]


def test_every_imported_test_is_flagged_for_review(db, clean_graph, catalogue_path):
    """Honest outcome: the catalogue specifies what to test, not how, so every
    test needs a specialist before it can run."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    records = (
        db.execute(
            select(CatalogueImportRecord).where(
                CatalogueImportRecord.target_table == "control_tests"
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == EXPECTED_TESTS
    assert all(r.needs_review for r in records)
    assert all(vocab.NO_EXECUTABLE_RULE in r.review_reasons for r in records)


def test_source_reference_cites_the_catalogue_entry(db, clean_graph, catalogue_path):
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    version = (
        db.execute(
            select(ControlTestVersion)
            .join(ControlTest)
            .where(ControlTest.test_code == "FAT-001")
        )
        .scalars()
        .one()
    )
    assert "FAT-001" in version.source_reference
    assert "catalogue v2.0" in version.source_reference


def test_checksum_changes_when_the_source_changes(db, clean_graph, catalogue_path):
    """So a reviewer can tell imported content came from a different revision."""
    before = load_catalogue(catalogue_path).checksum

    payload = json.loads(catalogue_path.read_text())
    payload["controls"][0]["name"] = "Edited"
    _write(catalogue_path, payload)

    assert load_catalogue(catalogue_path).checksum != before


# --- Coexistence with the illustrative sample -----------------------------


def test_import_does_not_disturb_the_sample_graph(db, catalogue_path, control_graph):
    """The hand-written sample is namespaced SMP-*; the import uses the
    catalogue's own ids. Neither may capture the other's records."""
    sample_test_ids = {
        t.id
        for t in db.execute(
            select(ControlTest).where(ControlTest.test_code.like("SMP-%"))
        )
        .scalars()
        .all()
    }
    sample_control_id = control_graph.fatigue_control.id

    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    still_there = {
        t.id
        for t in db.execute(
            select(ControlTest).where(ControlTest.test_code.like("SMP-%"))
        )
        .scalars()
        .all()
    }
    assert sample_test_ids == still_there

    # The sample's tests must still belong to the sample's control.
    for test in db.execute(
        select(ControlTest).where(ControlTest.test_code.like("SMP-FAT-%"))
    ).scalars().all():
        assert test.control_id == sample_control_id


def test_import_reuses_the_existing_hvnl_regulation(db, catalogue_path, control_graph):
    """Both describe the same law; a second HVNL row would be a duplicate."""
    import_catalogue(db, catalogue_path, effective_from=EFFECTIVE_FROM)

    hvnl = (
        db.execute(select(Regulation).where(Regulation.regulation_code == "HVNL"))
        .scalars()
        .all()
    )
    assert len(hvnl) == 1
