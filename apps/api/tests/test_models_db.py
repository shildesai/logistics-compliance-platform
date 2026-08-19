"""Integration tests for the ORM layer against a real PostgreSQL database.

The models use PostgreSQL-specific column types (UUID), so these cannot run on
SQLite. They are skipped when no database is reachable, keeping the rest of the
suite runnable without infrastructure.
"""

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.models import Organization, User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        with eng.connect():
            pass
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"No database reachable for ORM tests: {exc}")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    """Each test runs in a transaction that is rolled back, so tests never
    leave rows behind or depend on each other's data."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)
    try:
        yield db
    finally:
        db.close()
        # A test that asserts on an IntegrityError leaves the transaction
        # already aborted, so only roll back if it is still active.
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def test_organization_and_user_persist_with_relationship(session):
    org = Organization(name="Southern Cross Logistics", slug=f"scl-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.flush()

    user = User(
        organization_id=org.id,
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        full_name="Sam Chen",
    )
    session.add(user)
    session.flush()

    assert isinstance(org.id, uuid.UUID)
    assert user.role == "compliance_manager", "default role should be applied"

    loaded = session.execute(select(User).where(User.id == user.id)).scalar_one()
    assert loaded.organization.name == "Southern Cross Logistics"
    assert loaded in org.users


def test_organization_slug_is_unique(session):
    slug = f"dupe-{uuid.uuid4().hex[:8]}"
    session.add(Organization(name="First", slug=slug))
    session.flush()

    session.add(Organization(name="Second", slug=slug))
    with pytest.raises(IntegrityError):
        session.flush()


def test_user_email_is_unique(session):
    org = Organization(name="Org", slug=f"org-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.flush()

    email = f"{uuid.uuid4().hex[:8]}@example.com"
    session.add(User(organization_id=org.id, email=email, full_name="A"))
    session.flush()

    session.add(User(organization_id=org.id, email=email, full_name="B"))
    with pytest.raises(IntegrityError):
        session.flush()
