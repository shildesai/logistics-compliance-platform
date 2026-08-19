"""Platform roles and the permissions each role grants.

Roles are a fixed platform concept, not tenant-editable data: each role maps to
a permission set defined in code and enforced at the API boundary. They are
therefore modelled as an enum rather than a database table — a tenant cannot
invent a role, and a role's meaning cannot drift per-tenant. See
docs/TENANCY.md for the rationale.
"""

from enum import StrEnum


class Role(StrEnum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    COMPLIANCE_MANAGER = "COMPLIANCE_MANAGER"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"
    EXECUTIVE = "EXECUTIVE"
    AUDITOR = "AUDITOR"
    READ_ONLY = "READ_ONLY"


class Permission(StrEnum):
    # Reading organisation-scoped data.
    ORG_READ = "org:read"
    # Editing the organisation profile (name, legal name, ABN).
    ORG_MANAGE = "org:manage"
    # Adding/removing members and changing their roles.
    MEMBERS_MANAGE = "members:manage"
    # Assigning jurisdictions and CoR roles, recording accreditation.
    APPLICABILITY_MANAGE = "applicability:manage"
    # Operational reference data: sites, business units, fleets, suppliers.
    OPERATIONS_MANAGE = "operations:manage"
    # Cross-organisation access. Platform staff only.
    PLATFORM_ADMIN = "platform:admin"


_READ_ONLY_SET = frozenset({Permission.ORG_READ})

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.PLATFORM_ADMIN: frozenset(Permission),
    Role.ORG_ADMIN: frozenset(
        {
            Permission.ORG_READ,
            Permission.ORG_MANAGE,
            Permission.MEMBERS_MANAGE,
            Permission.APPLICABILITY_MANAGE,
            Permission.OPERATIONS_MANAGE,
        }
    ),
    # Owns which obligations apply and the accreditation record, but not
    # billing-style org profile edits or membership.
    Role.COMPLIANCE_MANAGER: frozenset(
        {
            Permission.ORG_READ,
            Permission.APPLICABILITY_MANAGE,
        }
    ),
    # Owns the operational footprint: sites, fleets, business units, suppliers.
    Role.OPERATIONS_MANAGER: frozenset(
        {
            Permission.ORG_READ,
            Permission.OPERATIONS_MANAGE,
        }
    ),
    # Oversight roles. Deliberately read-only: an auditor who can edit the
    # records they are assessing has no evidentiary value.
    Role.EXECUTIVE: _READ_ONLY_SET,
    Role.AUDITOR: _READ_ONLY_SET,
    Role.READ_ONLY: _READ_ONLY_SET,
}

# Roles that may be assigned to a user within an organisation. PLATFORM_ADMIN
# is a property of the user account itself, not an organisation membership —
# granting it per-organisation would let an org admin escalate to cross-tenant
# access, which is exactly what tenancy must prevent.
ASSIGNABLE_ORG_ROLES: frozenset[Role] = frozenset(
    {
        Role.ORG_ADMIN,
        Role.COMPLIANCE_MANAGER,
        Role.OPERATIONS_MANAGER,
        Role.EXECUTIVE,
        Role.AUDITOR,
        Role.READ_ONLY,
    }
)


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]
