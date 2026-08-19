"""API smoke tests: every /api/v1 route the frontend shell depends on
responds successfully with the expected shape, and errors are structured.
"""

import pytest

ORG_SLUG = "southern-cross-logistics"


def test_list_organizations(client):
    response = client.get("/api/v1/organizations")

    assert response.status_code == 200
    orgs = response.json()
    assert len(orgs) == 3
    assert {"id", "name", "slug"} <= orgs[0].keys()


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/dashboard/overview",
        "/api/v1/dashboard/evidence",
        "/api/v1/dashboard/findings",
        "/api/v1/dashboard/corrective-actions",
        "/api/v1/dashboard/audit-pack",
    ],
)
def test_dashboard_endpoints_respond_successfully(client, path):
    response = client.get(path, params={"org": ORG_SLUG})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_overview_shape(client):
    response = client.get("/api/v1/dashboard/overview", params={"org": ORG_SLUG})

    body = response.json()
    assert body["organization_slug"] == ORG_SLUG
    assert isinstance(body["domains"], list)
    assert len(body["domains"]) == 8
    for domain in body["domains"]:
        assert {"present", "suitable", "operating", "effective"} == domain["psoe"].keys()


def test_unknown_organization_returns_structured_404(client):
    response = client.get("/api/v1/dashboard/overview", params={"org": "does-not-exist"})

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["path"] == "/api/v1/dashboard/overview"
    assert "timestamp" in body["error"]


def test_unmatched_route_returns_structured_404(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_error"
