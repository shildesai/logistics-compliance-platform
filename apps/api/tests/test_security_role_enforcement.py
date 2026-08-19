"""Role enforcement: having access to an organisation is not having every
permission within it."""

import uuid

import pytest

from tests.conftest import auth


def _new_site_payload() -> dict:
    return {"name": "Depot", "code": f"d-{uuid.uuid4().hex[:6]}"}


@pytest.mark.parametrize("actor", ["read_only", "auditor"])
def test_read_only_roles_cannot_create_operational_records(client, two_tenants, actor):
    response = client.post(
        "/api/v1/sites",
        json=_new_site_payload(),
        headers=auth(getattr(two_tenants.a, actor), two_tenants.a.organisation),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("actor", ["read_only", "auditor"])
def test_read_only_roles_can_still_read(client, two_tenants, actor):
    response = client.get(
        "/api/v1/sites",
        headers=auth(getattr(two_tenants.a, actor), two_tenants.a.organisation),
    )
    assert response.status_code == 200


def test_auditor_cannot_edit_the_organisation_profile(client, two_tenants):
    response = client.patch(
        "/api/v1/organisation",
        json={"name": "Auditor Was Here"},
        headers=auth(two_tenants.a.auditor, two_tenants.a.organisation),
    )
    assert response.status_code == 403


def test_operations_manager_can_manage_operations_but_not_applicability(
    client, two_tenants, jurisdictions
):
    actor = two_tenants.a.operations_manager
    headers = auth(actor, two_tenants.a.organisation)

    allowed = client.post("/api/v1/sites", json=_new_site_payload(), headers=headers)
    assert allowed.status_code == 201

    denied = client.put(
        "/api/v1/organisation/jurisdictions",
        json={"jurisdiction_ids": [str(jurisdictions[0].id)]},
        headers=headers,
    )
    assert denied.status_code == 403


def test_compliance_manager_can_manage_applicability_but_not_operations(
    client, two_tenants, jurisdictions
):
    actor = two_tenants.a.compliance_manager
    headers = auth(actor, two_tenants.a.organisation)

    allowed = client.put(
        "/api/v1/organisation/jurisdictions",
        json={"jurisdiction_ids": [str(jurisdictions[0].id)]},
        headers=headers,
    )
    assert allowed.status_code == 200

    denied = client.post("/api/v1/sites", json=_new_site_payload(), headers=headers)
    assert denied.status_code == 403


def test_org_admin_can_do_both(client, two_tenants, jurisdictions):
    headers = auth(two_tenants.a.admin, two_tenants.a.organisation)

    assert client.post("/api/v1/sites", json=_new_site_payload(), headers=headers).status_code == 201
    assert (
        client.put(
            "/api/v1/organisation/jurisdictions",
            json={"jurisdiction_ids": [str(jurisdictions[0].id)]},
            headers=headers,
        ).status_code
        == 200
    )


def test_role_catalogue_is_exposed(client, two_tenants):
    response = client.get("/api/v1/roles", headers={"X-User-Id": str(two_tenants.a.admin.id)})
    assert response.status_code == 200

    catalogue = {row["role"]: row for row in response.json()}
    assert set(catalogue) == {
        "PLATFORM_ADMIN",
        "ORG_ADMIN",
        "COMPLIANCE_MANAGER",
        "OPERATIONS_MANAGER",
        "EXECUTIVE",
        "AUDITOR",
        "READ_ONLY",
    }
    assert catalogue["PLATFORM_ADMIN"]["assignable_in_organisation"] is False
    assert catalogue["ORG_ADMIN"]["assignable_in_organisation"] is True
