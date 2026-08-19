"""Unit tests for the synthetic dashboard fixture data.

These only check internal consistency of the fixtures (Phase 1 has no real
compliance logic to test) — see docs/DECISIONS.md.
"""

from app.data.synthetic import (
    OPEN_FINDING_STATUSES,
    synthetic_audit_pack,
    synthetic_corrective_actions,
    synthetic_domain_statuses,
    synthetic_evidence,
    synthetic_findings,
)


def test_domain_statuses_cover_all_eight_p1_domains():
    domains = synthetic_domain_statuses()
    assert len(domains) == 8
    assert len({d.domain for d in domains}) == 8


def test_domain_control_counts_match_catalogue_totals():
    domains = {d.domain: d.control_count for d in synthetic_domain_statuses()}
    # Matches docs/DECISIONS.md §1.1: 47 P1 tests across these 8 domains.
    assert sum(domains.values()) == 47


def test_overview_open_findings_agree_with_the_findings_inbox():
    """The Assurance Overview must not claim more open findings than the
    Findings inbox actually lists — the two views share one source of truth."""
    per_domain = {d.domain: d.open_findings for d in synthetic_domain_statuses()}
    findings = synthetic_findings()

    for domain, claimed in per_domain.items():
        actual = sum(
            1 for f in findings if f.domain == domain and f.status in OPEN_FINDING_STATUSES
        )
        assert claimed == actual, f"{domain}: overview says {claimed}, inbox has {actual}"

    open_total = sum(1 for f in findings if f.status in OPEN_FINDING_STATUSES)
    assert sum(per_domain.values()) == open_total


def test_every_finding_belongs_to_a_known_domain():
    known_domains = {d.domain for d in synthetic_domain_statuses()}
    for finding in synthetic_findings():
        assert finding.domain in known_domains


def test_findings_reference_known_control_tests():
    findings = synthetic_findings()
    assert len(findings) > 0
    for finding in findings:
        assert finding.status in {"potential", "confirmed", "rejected"}
        assert 0.0 <= finding.confidence <= 1.0


def test_corrective_actions_reference_existing_findings():
    finding_ids = {f.finding_id for f in synthetic_findings()}
    for car in synthetic_corrective_actions():
        assert car.finding_id in finding_ids


def test_evidence_items_have_required_fields():
    for item in synthetic_evidence():
        assert item.evidence_id
        assert item.source_system
        assert item.control_test_id


def test_audit_pack_has_no_negative_counts():
    for domain in synthetic_audit_pack():
        assert domain.population >= 0
        assert domain.exceptions >= 0
        assert domain.exceptions <= domain.population
