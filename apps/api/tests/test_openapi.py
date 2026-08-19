def test_openapi_schema_is_served(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"]
    assert "/api/v1/dashboard/overview" in schema["paths"]


def test_docs_ui_is_served(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
