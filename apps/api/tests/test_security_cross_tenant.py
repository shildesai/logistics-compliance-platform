"""Security tests: cross-tenant data must be unreachable.

These are the tests that make the tenancy claim falsifiable. Each one takes a
user who legitimately belongs to organisation A and tries to reach organisation
B's data by a different route. All of them must fail closed.

A note on status codes: cross-tenant access returns **404, not 403**. A 403
would confirm that the requested id exists somewhere on the platform, which is
itself a cross-tenant leak. Several tests assert on this specifically.
"""

import uuid

import pytest

from tests.conftest import auth

# Every tenant-scoped collection endpoint.
COLLECTION_ENDPOINTS = [
    "/api/v1/organisation",
    "/api/v1/organisation/members",
    "/api/v1/organisation/jurisdictions",
    "/api/v1/organisation/cor-roles",
    "/api/v1/organisation/accreditations",
    "/api/v1/business-units",
    "/api/v1/sites",
    "/api/v1/fleets",
    "/api/v1/suppliers",
    "/api/v1/dashboard/overview",
    "/api/v1/dashboard/evidence",
    "/api/v1/dashboard/findings",
    "/api/v1/dashboard/corrective-actions",
    "/api/v1/dashboard/audit-pack",
]


# --- Authentication is required at all -----------------------------------


@pytest.mark.parametrize("path", COLLECTION_ENDPOINTS)
def test_endpoints_reject_unauthenticated_callers(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_forged_user_id_is_rejected(client):
    response = client.get(
        "/api/v1/sites", headers={"X-User-Id": str(uuid.uuid4())}
    )
    assert response.status_code == 401


# --- Naming another tenant's organisation --------------------------------


@pytest.mark.parametrize("path", COLLECTION_ENDPOINTS)
def test_user_cannot_target_an_organisation_they_do_not_belong_to(
    client, two_tenants, path
):
    """The core case: a valid user of org A pointing the API at org B."""
    response = client.get(
        path, headers=auth(two_tenants.a.admin, two_tenants.b.organisation)
    )
    assert response.status_code == 404, (
        f"{path} leaked access to another tenant (status {response.status_code})"
    )
    assert response.json()["error"]["code"] == "not_found"


def test_membership_in_one_org_does_not_imply_the_other(client, two_tenants):
    a_ok = client.get("/api/v1/sites", headers=auth(two_tenants.a.admin, two_tenants.a.organisation))
    b_denied = client.get(
        "/api/v1/sites", headers=auth(two_tenants.a.admin, two_tenants.b.organisation)
    )
    assert a_ok.status_code == 200
    assert b_denied.status_code == 404


def test_org_query_parameter_is_also_verified(client, two_tenants):
    """The organisation may be supplied as ?org= — it is verified identically."""
    response = client.get(
        "/api/v1/sites",
        params={"org": str(two_tenants.b.organisation.id)},
        headers={"X-User-Id": str(two_tenants.a.admin.id)},
    )
    assert response.status_code == 404


def test_request_without_an_organisation_is_refused(client, two_tenants):
    response = client.get("/api/v1/sites", headers={"X-User-Id": str(two_tenants.a.admin.id)})
    assert response.status_code == 404


# --- Fetching another tenant's records by id ------------------------------


def test_cannot_read_another_tenants_site_by_id(client, two_tenants):
    """Even while correctly scoped to their own org, a user cannot pull a
    record id belonging to another organisation."""
    response = client.get(
        f"/api/v1/sites/{two_tenants.b.site.id}",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "collection,attr",
    [
        ("sites", "site"),
        ("fleets", "fleet"),
        ("suppliers", "supplier"),
        ("business-units", "business_unit"),
    ],
)
def test_cannot_read_another_tenants_record_by_id(client, two_tenants, collection, attr):
    foreign_id = getattr(two_tenants.b, attr).id
    response = client.get(
        f"/api/v1/{collection}/{foreign_id}",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 404


def test_cross_tenant_id_is_indistinguishable_from_a_random_id(client, two_tenants):
    """404 for both, so response codes cannot be used to probe for existence."""
    headers = auth(two_tenants.a.admin, two_tenants.a.organisation)

    real_but_foreign = client.get(f"/api/v1/sites/{two_tenants.b.site.id}", headers=headers)
    pure_fiction = client.get(f"/api/v1/sites/{uuid.uuid4()}", headers=headers)

    assert real_but_foreign.status_code == pure_fiction.status_code == 404
    assert real_but_foreign.json()["error"]["code"] == pure_fiction.json()["error"]["code"]


def test_cannot_delete_another_tenants_record(client, two_tenants, db):
    from app.models import Site

    response = client.delete(
        f"/api/v1/sites/{two_tenants.b.site.id}",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 404
    assert db.get(Site, two_tenants.b.site.id) is not None, "foreign record was deleted"


# --- Listings never contain another tenant's rows -------------------------


@pytest.mark.parametrize(
    "collection,attr", [("sites", "site"), ("fleets", "fleet"), ("suppliers", "supplier")]
)
def test_listings_contain_only_the_callers_organisation(
    client, two_tenants, collection, attr
):
    response = client.get(
        f"/api/v1/{collection}",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 200
    returned_ids = {row["id"] for row in response.json()}

    assert str(getattr(two_tenants.a, attr).id) in returned_ids
    assert str(getattr(two_tenants.b, attr).id) not in returned_ids


def test_member_listing_does_not_leak_other_tenants_users(client, two_tenants):
    response = client.get(
        "/api/v1/organisation/members",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 200
    emails = {m["email"] for m in response.json()}

    assert two_tenants.a.admin.email in emails
    assert two_tenants.b.admin.email not in emails


def test_organisation_switcher_lists_only_your_memberships(client, two_tenants):
    response = client.get(
        "/api/v1/me/organisations", headers={"X-User-Id": str(two_tenants.a.admin.id)}
    )
    assert response.status_code == 200
    org_ids = {m["organisation"]["id"] for m in response.json()}

    assert org_ids == {str(two_tenants.a.organisation.id)}
    assert str(two_tenants.b.organisation.id) not in org_ids


# --- Writes cannot escape the tenant --------------------------------------


def test_created_records_are_stamped_with_the_callers_organisation(client, two_tenants, db):
    from app.models import Site

    response = client.post(
        "/api/v1/sites",
        json={"name": "New Depot", "code": f"nd-{uuid.uuid4().hex[:6]}"},
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 201

    created = db.get(Site, uuid.UUID(response.json()["id"]))
    assert created.organisation_id == two_tenants.a.organisation.id


def test_organisation_id_in_the_request_body_is_ignored(client, two_tenants, db):
    """A client cannot plant a record in another tenant by supplying its id."""
    from app.models import Site

    response = client.post(
        "/api/v1/sites",
        json={
            "name": "Smuggled Depot",
            "code": f"sd-{uuid.uuid4().hex[:6]}",
            "organisation_id": str(two_tenants.b.organisation.id),
        },
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 201

    created = db.get(Site, uuid.UUID(response.json()["id"]))
    assert created.organisation_id == two_tenants.a.organisation.id, (
        "request body overrode the tenant scope"
    )


def test_cannot_parent_a_record_to_another_tenants_record(client, two_tenants):
    """Foreign keys alone cannot express 'same tenant'; this is checked."""
    response = client.post(
        "/api/v1/business-units",
        json={
            "name": "Child",
            "code": f"ch-{uuid.uuid4().hex[:6]}",
            "parent_id": str(two_tenants.b.business_unit.id),
        },
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 404


def test_cannot_attach_a_fleet_to_another_tenants_site(client, two_tenants):
    response = client.post(
        "/api/v1/fleets",
        json={
            "name": "Fleet",
            "code": f"fl-{uuid.uuid4().hex[:6]}",
            "home_site_id": str(two_tenants.b.site.id),
        },
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )
    assert response.status_code == 404


def test_cannot_edit_another_tenants_organisation_profile(client, two_tenants, db):
    from app.models import Organisation

    original = two_tenants.b.organisation.name
    response = client.patch(
        "/api/v1/organisation",
        json={"name": "Renamed By Attacker"},
        headers=auth(two_tenants.a.admin, two_tenants.b.organisation),
    )
    assert response.status_code == 404
    db.expire_all()
    assert db.get(Organisation, two_tenants.b.organisation.id).name == original


def test_cannot_update_another_tenants_accreditation(client, two_tenants):
    response = client.put(
        f"/api/v1/organisation/accreditations/{two_tenants.b.accreditation.id}",
        json={"scheme": "HVA", "module": "MASS", "status": "WITHDRAWN"},
        headers=auth(two_tenants.a.compliance_manager, two_tenants.a.organisation),
    )
    assert response.status_code == 404


# --- Platform administrators: elevation must be explicit ------------------


def test_platform_admin_may_act_across_organisations(client, two_tenants):
    """The one intentional exception. It is a property of the user account,
    not something an organisation administrator can grant."""
    for org in (two_tenants.a.organisation, two_tenants.b.organisation):
        response = client.get(
            "/api/v1/sites", headers=auth(two_tenants.platform_admin, org)
        )
        assert response.status_code == 200


def test_platform_admin_still_cannot_reach_a_nonexistent_organisation(client, two_tenants):
    response = client.get(
        "/api/v1/sites",
        headers={
            "X-User-Id": str(two_tenants.platform_admin.id),
            "X-Organisation-Id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 404


def test_org_admin_is_not_a_platform_admin(client, two_tenants):
    """Confirms the privilege boundary the role model depends on."""
    assert two_tenants.a.admin.is_platform_admin is False
    response = client.get(
        "/api/v1/me/organisations", headers={"X-User-Id": str(two_tenants.a.admin.id)}
    )
    assert len(response.json()) == 1
