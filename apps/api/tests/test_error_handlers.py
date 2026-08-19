"""Unit tests for the structured error handlers.

The dashboard routes deliberately have no failing inputs, so the validation
(422) and unexpected-error (500) branches are exercised here against a
throwaway app that registers the real production handlers.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import AppError, NotFoundError, register_exception_handlers


@pytest.fixture()
def error_app_client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/needs-int")
    def needs_int(count: int) -> dict:  # 422 when `count` isn't an int
        return {"count": count}

    @app.get("/boom")
    def boom() -> dict:
        raise RuntimeError("something failed deep in the stack")

    @app.get("/missing")
    def missing() -> dict:
        raise NotFoundError("No such thing")

    @app.get("/app-error")
    def app_error() -> dict:
        raise AppError(code="custom_code", message="Custom failure", status_code=409)

    # raise_server_exceptions=False so the 500 handler's response is returned
    # rather than the exception being re-raised into the test.
    return TestClient(app, raise_server_exceptions=False)


def test_validation_error_returns_structured_422(error_app_client):
    response = error_app_client.get("/needs-int", params={"count": "not-a-number"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"] == "Request validation failed"
    assert error["path"] == "/needs-int"
    assert error["timestamp"]
    # Field-level detail is preserved so clients can point at the bad input.
    assert isinstance(error["details"], list) and error["details"]


def test_unexpected_exception_returns_structured_500(error_app_client):
    response = error_app_client.get("/boom")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["path"] == "/boom"
    # The internal exception message must not leak to the client.
    assert "something failed deep in the stack" not in response.text


def test_not_found_error_returns_structured_404(error_app_client):
    response = error_app_client.get("/missing")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"] == "No such thing"


def test_app_error_preserves_code_and_status(error_app_client):
    response = error_app_client.get("/app-error")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "custom_code"
    assert error["message"] == "Custom failure"
