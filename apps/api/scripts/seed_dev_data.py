"""Seed development data: two organisations, users in each, and some records.

Development convenience only — never run against production. Two organisations
are created deliberately so that tenant isolation is visible while developing:
signing in as an Alpha user must never surface Bravo's data.

    python scripts/seed_dev_data.py

Prints the user ids to put in apps/web/.env.local as NEXT_PUBLIC_DEV_USER_ID.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.roles import Role  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.models import (  # noqa: E402
    Accreditation,
    AccreditationModule,
    AccreditationScheme,
    AccreditationStatus,
    BusinessUnit,
    CoRRole,
    Fleet,
    Jurisdiction,
    Organisation,
    OrganisationCoRRole,
    OrganisationJurisdiction,
    OrganisationUser,
    Site,
    SiteType,
    Supplier,
    SupplierType,
    User,
)

PRODUCTION_LIKE = {"production", "prod", "staging"}


def _get_or_create_org(db: Session, *, name: str, slug: str, abn: str) -> Organisation:
    org = db.execute(select(Organisation).where(Organisation.slug == slug)).scalar_one_or_none()
    if org is None:
        org = Organisation(name=name, slug=slug, legal_name=f"{name} Pty Ltd", abn=abn)
        db.add(org)
        db.flush()
    return org


#: Namespace for deriving stable dev user ids from email addresses. Re-seeding
#: a rebuilt database therefore produces the *same* ids, so the value in
#: apps/web/.env.local keeps working instead of going stale every reset.
DEV_ID_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def _dev_user_id(email: str) -> uuid.UUID:
    return uuid.uuid5(DEV_ID_NAMESPACE, email)


def _get_or_create_user(
    db: Session, *, email: str, full_name: str, platform_admin: bool = False
) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(
            id=_dev_user_id(email),
            email=email,
            full_name=full_name,
            is_platform_admin=platform_admin,
        )
        db.add(user)
        db.flush()
    return user


def _ensure_membership(db: Session, org: Organisation, user: User, role: Role) -> None:
    existing = db.execute(
        select(OrganisationUser).where(
            OrganisationUser.organisation_id == org.id,
            OrganisationUser.user_id == user.id,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(OrganisationUser(organisation_id=org.id, user_id=user.id, role=role))
        db.flush()


def _seed_org(db: Session, org: Organisation, *, jurisdiction_codes: list[str],
              cor_role_codes: list[str], accredited: bool) -> None:
    if db.execute(
        select(Site).where(Site.organisation_id == org.id)
    ).scalars().first() is None:
        bu = BusinessUnit(organisation_id=org.id, name="Linehaul", code="LH")
        db.add(bu)
        db.flush()

        nsw = db.execute(select(Jurisdiction).where(Jurisdiction.code == "NSW")).scalar_one()
        site = Site(
            organisation_id=org.id,
            name=f"{org.name} Depot",
            code="DEPOT-1",
            site_type=SiteType.DEPOT,
            jurisdiction_id=nsw.id,
            business_unit_id=bu.id,
            suburb="Eastern Creek",
            postcode="2766",
        )
        db.add(site)
        db.flush()

        db.add(
            Fleet(
                organisation_id=org.id,
                name="Primary Fleet",
                code="FLEET-1",
                business_unit_id=bu.id,
                home_site_id=site.id,
                vehicle_count=42,
            )
        )
        db.add(
            Supplier(
                organisation_id=org.id,
                name="Contracted Carrier Co.",
                code="SUP-1",
                supplier_type=SupplierType.SUBCONTRACTOR,
                abn="51824753556",
            )
        )

    for code in jurisdiction_codes:
        jurisdiction = db.execute(
            select(Jurisdiction).where(Jurisdiction.code == code)
        ).scalar_one()
        exists = db.execute(
            select(OrganisationJurisdiction).where(
                OrganisationJurisdiction.organisation_id == org.id,
                OrganisationJurisdiction.jurisdiction_id == jurisdiction.id,
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                OrganisationJurisdiction(
                    organisation_id=org.id, jurisdiction_id=jurisdiction.id
                )
            )

    for code in cor_role_codes:
        cor_role = db.execute(select(CoRRole).where(CoRRole.code == code)).scalar_one()
        exists = db.execute(
            select(OrganisationCoRRole).where(
                OrganisationCoRRole.organisation_id == org.id,
                OrganisationCoRRole.cor_role_id == cor_role.id,
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(OrganisationCoRRole(organisation_id=org.id, cor_role_id=cor_role.id))

    # Only one of the two demo organisations holds accreditation, so the UI is
    # exercised in both states. The unaccredited one is NOT in a worse
    # compliance position — accreditation is voluntary.
    if accredited and db.execute(
        select(Accreditation).where(Accreditation.organisation_id == org.id)
    ).scalars().first() is None:
        db.add(
            Accreditation(
                organisation_id=org.id,
                scheme=AccreditationScheme.HVA,
                module=AccreditationModule.MASS,
                status=AccreditationStatus.ACCREDITED,
                accreditation_number="HVA-123456",
            )
        )


def main() -> None:
    settings = get_settings()
    if settings.environment.lower() in PRODUCTION_LIKE:
        raise SystemExit(
            f"Refusing to seed development data in environment='{settings.environment}'."
        )

    with Session(engine) as db:
        alpha = _get_or_create_org(
            db, name="Southern Cross Logistics", slug="southern-cross-logistics",
            abn="53004085616",
        )
        bravo = _get_or_create_org(
            db, name="Outback Freight Co.", slug="outback-freight-co", abn="29002589460"
        )

        alpha_admin = _get_or_create_user(
            db, email="sam.chen@southerncross.example", full_name="Sam Chen"
        )
        alpha_auditor = _get_or_create_user(
            db, email="ravi.patel@auditpartner.example", full_name="Ravi Patel"
        )
        bravo_admin = _get_or_create_user(
            db, email="jo.alvarez@outbackfreight.example", full_name="Jo Alvarez"
        )
        platform_admin = _get_or_create_user(
            db, email="platform.ops@example.com", full_name="Platform Operations",
            platform_admin=True,
        )

        _ensure_membership(db, alpha, alpha_admin, Role.ORG_ADMIN)
        _ensure_membership(db, alpha, alpha_auditor, Role.AUDITOR)
        _ensure_membership(db, bravo, bravo_admin, Role.ORG_ADMIN)

        _seed_org(
            db, alpha,
            jurisdiction_codes=["NSW", "VIC", "QLD"],
            cor_role_codes=["OPERATOR", "EMPLOYER", "SCHEDULER"],
            accredited=True,
        )
        _seed_org(
            db, bravo,
            jurisdiction_codes=["SA", "NT"],
            cor_role_codes=["OPERATOR", "CONSIGNOR"],
            accredited=False,
        )

        db.commit()

        print("Seeded development data.\n")
        print("Sign in as one of these by setting NEXT_PUBLIC_DEV_USER_ID:\n")
        for label, user in [
            ("Sam Chen        (ORG_ADMIN, Southern Cross)", alpha_admin),
            ("Ravi Patel      (AUDITOR,   Southern Cross)", alpha_auditor),
            ("Jo Alvarez      (ORG_ADMIN, Outback Freight)", bravo_admin),
            ("Platform Ops    (PLATFORM_ADMIN, all orgs)", platform_admin),
        ]:
            print(f"  {label}\n    {user.id}")


if __name__ == "__main__":
    main()
