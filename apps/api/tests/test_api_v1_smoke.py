"""API smoke tests: the routes the frontend shell depends on respond
successfully for an authenticated member, and errors stay structured."""

import pytest

from tests.conftest import auth

DASHBOARD_PATHS = [
    "/api/v1/dashboard/overview",
    "/api/v1/dashboard/evidence",
    "/api/v1/dashboard/findings",
    "/api/v1/dashboard/corrective-actions",
    "/api/v1/dashboard/audit-pack",
]


@pytest.mark.parametrize("path", DASHBOARD_PATHS)
def test_dashboard_endpoints_respond_successfully(client, two_tenants, path):
    response = client.get(
        path, headers=auth(two_tenants.a.admin, two_tenants.a.organisation)
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_overview_shape(client, two_tenants):
    response = client.get(
        "/api/v1/dashboard/overview",
        headers=auth(two_tenants.a.admin, two_tenants.a.organisation),
    )

    body = response.json()
    assert body["organisation_id"] == str(two_tenants.a.organisation.id)
    assert len(body["domains"]) == 8
    for domain in body["domains"]:
        assert {"present", "suitable", "operating", "effective"} == domain["psoe"].keys()


def test_me_returns_the_caller_and_their_memberships(client, two_tenants):
    response = client.get("/api/v1/me", headers={"X-User-Id": str(two_tenants.a.admin.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == two_tenants.a.admin.email
    assert body["is_platform_admin"] is False
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["role"] == "ORG_ADMIN"


def test_unknown_organisation_returns_structured_404(client, two_tenants):
    response = client.get(
        "/api/v1/dashboard/overview",
        params={"org": "00000000-0000-0000-0000-000000000000"},
        headers={"X-User-Id": str(two_tenants.a.admin.id)},
    )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["path"] == "/api/v1/dashboard/overview"
    assert "timestamp" in error


def test_unmatched_route_returns_structured_404(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
