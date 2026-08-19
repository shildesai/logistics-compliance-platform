from fastapi import APIRouter

from app.schemas.organization import OrganizationOut

router = APIRouter(prefix="/organizations", tags=["organizations"])

# Synthetic organisations for the top organisation selector. Real tenancy
# (persisted Organization rows, membership, auth) is a Phase 0 follow-up —
# see docs/DOMAIN_MODEL.md Identity & Tenancy context.
_SYNTHETIC_ORGS = [
    {"id": "9c1f7e2a-1111-4a3b-8b1a-000000000001", "name": "Southern Cross Logistics", "slug": "southern-cross-logistics"},
    {"id": "9c1f7e2a-2222-4a3b-8b1a-000000000002", "name": "Outback Freight Co.", "slug": "outback-freight-co"},
    {"id": "9c1f7e2a-3333-4a3b-8b1a-000000000003", "name": "Coastal Bulk Transport", "slug": "coastal-bulk-transport"},
]


@router.get("", response_model=list[OrganizationOut])
def list_organizations() -> list[dict]:
    return _SYNTHETIC_ORGS
