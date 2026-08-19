"""Test fixtures.

Tests run against the real migrated PostgreSQL schema (not `create_all`), so
they exercise the same DDL and seeded reference data that production would get.
Each test runs inside a transaction that is rolled back, so tests neither leak
rows nor depend on each other.

The `two_tenants` fixture builds the standing scenario used by the security
suite: two unrelated organisations, each with its own users and its own
operational records, plus a platform administrator.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.roles import Role
from app.db.session import get_db
from app.main import app
from app.models import (
    Accreditation,
    AccreditationModule,
    AccreditationScheme,
    AccreditationStatus,
    BusinessUnit,
    CoRRole,
    Fleet,
    Jurisdiction,
    Organisation,
    OrganisationUser,
    Site,
    Supplier,
    User,
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        with eng.connect() as conn:
            # Reference data comes from the migration; if it is missing the
            # database has not been migrated and the tests would be misleading.
            conn.execute(text("SELECT 1 FROM jurisdictions LIMIT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(
            f"No migrated database available ({exc}). Run `alembic upgrade head` first."
        )
    return eng


@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db) -> TestClient:
    """A client whose requests share the test's transaction."""
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@dataclass
class TenantFixture:
    organisation: Organisation
    admin: User
    read_only: User
    auditor: User
    compliance_manager: User
    operations_manager: User
    site: Site
    business_unit: BusinessUnit
    fleet: Fleet
    supplier: Supplier
    accreditation: Accreditation


@dataclass
class TwoTenants:
    a: TenantFixture
    b: TenantFixture
    platform_admin: User


def _make_user(db: Session, name: str, *, platform_admin: bool = False) -> User:
    user = User(
        email=f"{_unique(name)}@example.com",
        full_name=name.replace("-", " ").title(),
        is_platform_admin=platform_admin,
    )
    db.add(user)
    db.flush()
    return user


def _make_tenant(db: Session, label: str) -> TenantFixture:
    org = Organisation(name=f"Org {label}", slug=_unique(f"org-{label}"))
    db.add(org)
    db.flush()

    users: dict[str, User] = {}
    for key, role in [
        ("admin", Role.ORG_ADMIN),
        ("read_only", Role.READ_ONLY),
        ("auditor", Role.AUDITOR),
        ("compliance_manager", Role.COMPLIANCE_MANAGER),
        ("operations_manager", Role.OPERATIONS_MANAGER),
    ]:
        user = _make_user(db, f"{label}-{key}")
        db.add(
            OrganisationUser(organisation_id=org.id, user_id=user.id, role=role)
        )
        users[key] = user

    business_unit = BusinessUnit(
        organisation_id=org.id, name=f"{label} Linehaul", code=_unique("bu")
    )
    db.add(business_unit)
    db.flush()

    site = Site(organisation_id=org.id, name=f"{label} Depot", code=_unique("site"))
    fleet = Fleet(organisation_id=org.id, name=f"{label} Fleet", code=_unique("fleet"))
    supplier = Supplier(
        organisation_id=org.id, name=f"{label} Carrier", code=_unique("sup")
    )
    accreditation = Accreditation(
        organisation_id=org.id,
        scheme=AccreditationScheme.HVA,
        module=AccreditationModule.MASS,
        status=AccreditationStatus.ACCREDITED,
    )
    db.add_all([site, fleet, supplier, accreditation])
    db.flush()

    return TenantFixture(
        organisation=org,
        admin=users["admin"],
        read_only=users["read_only"],
        auditor=users["auditor"],
        compliance_manager=users["compliance_manager"],
        operations_manager=users["operations_manager"],
        site=site,
        business_unit=business_unit,
        fleet=fleet,
        supplier=supplier,
        accreditation=accreditation,
    )


@pytest.fixture()
def two_tenants(db) -> TwoTenants:
    return TwoTenants(
        a=_make_tenant(db, "alpha"),
        b=_make_tenant(db, "bravo"),
        platform_admin=_make_user(db, "platform-root", platform_admin=True),
    )


def auth(user: User, organisation: Organisation | None = None) -> dict[str, str]:
    """Headers authenticating as `user`, optionally acting in `organisation`."""
    headers = {"X-User-Id": str(user.id)}
    if organisation is not None:
        headers["X-Organisation-Id"] = str(organisation.id)
    return headers


#: Control-graph tables in FK-safe deletion order.
_GRAPH_TABLES_IN_DELETE_ORDER = (
    "CatalogueImportRecord",
    "RemediationTemplate",
    "EvidenceRequirement",
    "ControlTestVersion",
    "ControlTest",
    "ControlRiskLink",
    "ControlVersion",
    "Control",
    "ApplicabilityRule",
    "Risk",
    "Obligation",
    "RegulationVersion",
    "Regulation",
    "RegulatorySource",
)


@pytest.fixture()
def clean_graph(db):
    """Empty the control graph inside this test's transaction.

    The development database legitimately holds an imported catalogue, so a
    test that asserts on global counts would otherwise depend on ambient
    state. Deleting here gives a deterministic baseline and is rolled back
    with the rest of the transaction, leaving the dev data intact.
    """
    import app.models as models

    for name in _GRAPH_TABLES_IN_DELETE_ORDER:
        db.execute(delete(getattr(models, name)))
    db.flush()


@dataclass
class ControlGraphFixture:
    regulation: object
    fatigue_control: object
    maintenance_control: object


@pytest.fixture()
def control_graph(db, clean_graph) -> ControlGraphFixture:
    """The sample Compliance Control Graph, seeded inside the test transaction.

    Reuses scripts/seed_control_graph.py rather than duplicating fixtures, so
    the tests exercise the same data a developer sees locally — and the seed
    script itself gets tested on every run.
    """
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))

    from seed_control_graph import seed  # noqa: PLC0415

    # An ACTIVE version needs a recorded reviewer and approver.
    db.add(
        User(
            email=f"{_unique('graph-governor')}@example.com",
            full_name="Graph Governor",
            is_platform_admin=True,
        )
    )
    db.flush()

    seed(db)
    db.flush()

    from app.models import Control as _Control
    from app.models import Regulation as _Regulation

    regulation = db.execute(select(_Regulation)).scalars().one()
    controls = {
        c.control_code: c for c in db.execute(select(_Control)).scalars().all()
    }
    return ControlGraphFixture(
        regulation=regulation,
        fatigue_control=controls["SMP-CTL-FAT"],
        maintenance_control=controls["SMP-CTL-MNT"],
    )


@pytest.fixture()
def jurisdictions(db) -> list[Jurisdiction]:
    return list(db.execute(select(Jurisdiction).order_by(Jurisdiction.code)).scalars().all())


@pytest.fixture()
def cor_roles(db) -> list[CoRRole]:
    return list(db.execute(select(CoRRole).order_by(CoRRole.code)).scalars().all())
