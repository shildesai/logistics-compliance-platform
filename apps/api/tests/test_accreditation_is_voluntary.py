"""Accreditation is voluntary — the product must never imply otherwise.

Heavy Vehicle Accreditation is an optional scheme. An operator that has not
sought it is in good standing. These tests guard against the easy mistake of
treating "no accreditation record" as a compliance gap.
"""

import uuid

from app.models.accreditation import (
    ADVERSE_ACCREDITATION_STATUSES,
    AccreditationStatus,
)
from tests.conftest import auth


def test_not_accredited_is_not_an_adverse_status():
    """Never having sought a voluntary accreditation is not an adverse event."""
    assert AccreditationStatus.NOT_ACCREDITED not in ADVERSE_ACCREDITATION_STATUSES


def test_lapsed_states_are_adverse_but_never_having_applied_is_not():
    assert AccreditationStatus.SUSPENDED in ADVERSE_ACCREDITATION_STATUSES
    assert AccreditationStatus.EXPIRED in ADVERSE_ACCREDITATION_STATUSES
    assert AccreditationStatus.WITHDRAWN not in ADVERSE_ACCREDITATION_STATUSES
    assert AccreditationStatus.NOT_ACCREDITED not in ADVERSE_ACCREDITATION_STATUSES


def test_an_organisation_with_no_accreditation_record_is_served_normally(
    client, two_tenants, db
):
    """An empty accreditation list is a valid, unremarkable state: the request
    succeeds, returns an empty list, and carries no error or warning field."""
    from app.models import Accreditation

    db.delete(db.get(Accreditation, two_tenants.a.accreditation.id))
    db.flush()

    response = client.get(
        "/api/v1/organisation/accreditations",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_recording_not_accredited_is_a_valid_operation(client, two_tenants):
    """An operator can positively record that it has chosen not to seek
    accreditation, and that is stored as-is rather than rejected."""
    response = client.post(
        "/api/v1/organisation/accreditations",
        json={
            "scheme": "HVA",
            "module": "MAINTENANCE",
            "status": "NOT_ACCREDITED",
            "notes": "Assessed; accreditation not pursued.",
        },
        headers=auth(two_tenants.a.compliance_manager, two_tenants.a.organisation),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "NOT_ACCREDITED"


def test_accreditation_status_defaults_to_not_accredited(client, two_tenants):
    """The default must be the neutral state, not an implied requirement."""
    response = client.post(
        "/api/v1/organisation/accreditations",
        json={"scheme": "NHVAS", "module": "OTHER"},
        headers=auth(two_tenants.a.compliance_manager, two_tenants.a.organisation),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "NOT_ACCREDITED"


def test_no_compliance_score_is_derived_from_accreditation(client, two_tenants, db):
    """Removing an accreditation record must not change any dashboard figure.

    If this ever fails, something has started scoring operators on a voluntary
    scheme — see docs/DECISIONS.md and app/models/accreditation.py.
    """
    from app.models import Accreditation

    headers = auth(two_tenants.a.admin, two_tenants.a.organisation)
    before = client.get("/api/v1/dashboard/overview", headers=headers).json()

    db.delete(db.get(Accreditation, two_tenants.a.accreditation.id))
    db.flush()

    after = client.get("/api/v1/dashboard/overview", headers=headers).json()
    assert before == after
