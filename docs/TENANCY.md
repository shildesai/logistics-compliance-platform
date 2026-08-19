# Tenancy Model

How the platform keeps one customer's data away from another's.

This matters more here than in most SaaS products. Tenants are frequently
commercial competitors, and the data is safety-critical and potentially
discoverable in litigation or a regulatory investigation. A cross-tenant leak is
not an embarrassment to be patched later; it is an event a compliance-assurance
business would likely not survive.

Related: `docs/DOMAIN_MODEL.md` (bounded contexts), `docs/DECISIONS.md`
(architecture decisions), `docs/IMPLEMENTATION_PLAN.md` (phasing).

---

## 1. The isolation boundary

**The Organisation is the tenant.** Every operational record belongs to exactly
one organisation, and no query may return rows from more than one — with a single
deliberate exception (platform administrators, §5).

Three categories of table exist, and every table must be in exactly one:

| Category | Carries `organisation_id` | Examples |
|---|---|---|
| **Tenant-scoped** | Yes, `NOT NULL`, indexed | `sites`, `fleets`, `suppliers`, `business_units`, `accreditations`, `organisation_jurisdictions`, `organisation_cor_roles` |
| **Tenancy-defining** | Yes, but not subject to scoping | `organisation_users` — it *is* the authorisation source of truth |
| **Platform-scoped** | No | `organisations`, `users`, `jurisdictions`, `cor_roles` |

Tenant-scoped models inherit the `TenantScoped` mixin
(`app/db/mixins.py`), which supplies the column. Platform-scoped tables are
listed explicitly in `PLATFORM_SCOPED_TABLES` (`app/models/__init__.py`).

A test walks the SQLAlchemy registry and fails if a table appears in neither
list, so a new model cannot be added without someone making an isolation
decision. That test is
`test_every_table_is_either_tenant_scoped_or_explicitly_platform_scoped`.

### Why `users` is not tenant-scoped

A person may legitimately work across organisations — a compliance adviser
engaged by several operators, an auditor assessing multiple carriers. Their
account is global; their *access* to any organisation comes solely from an
`organisation_users` row. Nothing about holding an account grants access to any
organisation's data.

### Why suppliers are tenant-scoped

A `Supplier` row belongs to the organisation that engaged it. If that supplier is
also a platform customer, it is a separate `Organisation`, and neither party can
see the other's data. Governed cross-tenant sharing (the Compliance Passport) is
Phase 3 and is deliberately **not** modelled yet — see `docs/DECISIONS.md` §1.12.

---

## 2. Enforcement layers

Isolation is enforced at three points. Each is independently sufficient for the
common cases; together they mean a single mistake does not become a breach.

```
   Request
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ 1. resolve_principal        who is calling              │
│    app/api/deps.py          401 if unknown              │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ 2. resolve_tenant_context   which organisation,         │
│    app/api/deps.py          VERIFIED against membership │
│                             404 if not a member         │
└─────────────────────────────────────────────────────────┘
      │  TenantContext(principal, organisation_id, role)
      ▼
┌─────────────────────────────────────────────────────────┐
│ 3. TenantScopedRepository   every query filtered by     │
│    app/repositories/base.py organisation_id             │
│                             404 on foreign row          │
└─────────────────────────────────────────────────────────┘
```

### Layer 1 — Authentication

Establishes a `Principal` (user id, email, platform-admin flag). See §7 for the
current development shim and its guard rails.

### Layer 2 — Organisation resolution

The client names the organisation it wants to act in, via the
`X-Organisation-Id` header (or `?org=`). **That value is never trusted.** A
`TenantContext` is only returned after finding an `organisation_users` row
joining the caller to that organisation. The role on that row is the role the
request runs with — the client cannot assert its own role.

### Layer 3 — Tenant-scoped repository

`TenantScopedRepository` makes filtering structural rather than remembered:

1. **It cannot be constructed without a `TenantContext`.** There is no unscoped
   constructor and no default organisation.
2. **It refuses non-`TenantScoped` models** at construction time, so a model
   without an `organisation_id` cannot be accessed through it under the false
   impression that it is being filtered.
3. **Every query starts from `_scoped_select()`**, which applies the
   `organisation_id` predicate. Callers add predicates on top; they cannot
   remove that one.
4. **`add()` stamps `organisation_id` from the context**, never from the request
   body — so a client cannot create a record inside another tenant.

---

## 3. Why cross-tenant access returns 404, not 403

A `403 Forbidden` on another tenant's record confirms that the id exists
somewhere on the platform. That is itself a cross-tenant disclosure: an attacker
could enumerate ids and learn which ones are real.

So a record belonging to another organisation is reported **exactly as though it
does not exist**: `404`, same error code, same message shape as a random UUID.
`test_cross_tenant_id_is_indistinguishable_from_a_random_id` asserts this
directly.

The same reasoning applies to naming an organisation you are not a member of:
that is a 404, not a 403, so the organisation list cannot be probed.

`403` is reserved for the case where the caller legitimately belongs to the
organisation but their **role** does not permit the action — no existence
information leaks there, because they can already see the resource.

---

## 4. Roles and permissions

Roles are a fixed platform concept defined in `app/core/roles.py`, not
tenant-editable data. A tenant cannot invent a role, and a role's meaning cannot
drift between tenants. Each role maps to a permission set in code.

| Role | Read | Org profile | Members | Applicability | Operations | Cross-org |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `PLATFORM_ADMIN` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ORG_ADMIN` | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `COMPLIANCE_MANAGER` | ✓ | — | — | ✓ | — | — |
| `OPERATIONS_MANAGER` | ✓ | — | — | — | ✓ | — |
| `EXECUTIVE` | ✓ | — | — | — | — | — |
| `AUDITOR` | ✓ | — | — | — | — | — |
| `READ_ONLY` | ✓ | — | — | — | — | — |

"Applicability" covers jurisdictions, CoR roles and accreditation records —
the inputs that determine which obligations apply. "Operations" covers sites,
business units, fleets and suppliers.

Two deliberate choices:

- **`AUDITOR` is read-only.** An auditor who can edit the records they are
  assessing produces no evidentiary value. `EXECUTIVE` is read-only for the
  same reason — oversight, not operation.
- **The split between `COMPLIANCE_MANAGER` and `OPERATIONS_MANAGER` is not
  seniority, it is subject matter.** One owns which obligations apply; the other
  owns the operational footprint. Neither can do the other's job by default.

### Role is a modelled enum, not a table

`Role` is listed as an entity in the platform's requirements, but is implemented
as an enum plus a documented permission matrix, exposed read-only at
`GET /api/v1/roles`. The reason: permissions are enforced by code paths, so a
row in a `roles` table could not change what a role is actually allowed to do
without a code change anyway — a table would imply a configurability that does
not exist and could mislead an administrator into thinking they had changed
something.

---

## 5. Platform administrators — the one exception

`PLATFORM_ADMIN` is the single path to cross-organisation access, for platform
support work. Its constraints:

- It is a flag on the **user account** (`users.is_platform_admin`), never an
  organisation membership. An organisation administrator therefore **cannot**
  grant it — `PLATFORM_ADMIN` is excluded from `ASSIGNABLE_ORG_ROLES`, which
  closes the obvious privilege-escalation path.
- The elevation is written explicitly in `resolve_tenant_context`, as a branch
  that is reached only when no membership exists. It is never implied by a
  missing check.
- It still cannot reach an organisation that does not exist.

`test_platform_admin_is_not_a_platform_admin`-adjacent tests cover each of
these.

---

## 6. Applicability, and what the platform does *not* decide

Two tenant-scoped assignments drive which obligations apply:

- **Jurisdictions** (`organisation_jurisdictions`) — where the organisation
  operates. `jurisdictions.hvnl_participant` records that **WA and NT are not
  Heavy Vehicle National Law participants**; they run their own heavy-vehicle
  legislation, and rule packs for them are explicitly out of scope
  (`docs/DECISIONS.md` §1.7). The flag exists so HVNL logic is not silently
  applied where it does not hold.
- **CoR roles** (`organisation_cor_roles`) — which of the ten HVNL Chain of
  Responsibility party types apply. Several can apply at once, because CoR
  duties attach to what a business *does*, not what it calls itself.

Both are **self-declared determinations that the platform records**. The
platform does not make the legal assessment — consistent with the standing
principle that no automated component issues a compliance or legal conclusion.

### Accreditation is voluntary

Heavy Vehicle Accreditation is an **optional** scheme for eligible operators. It
is not required in order to operate, and most Chain of Responsibility duties
apply regardless. Two rules bind anything built on the `Accreditation` model:

1. **Absence of a record means "not recorded", not "non-compliant."** An empty
   accreditation list must never render as a gap, warning, finding, or score
   reduction.
2. **`NOT_ACCREDITED` is a neutral, legitimate end state.** An operator that has
   assessed accreditation and chosen not to pursue it is in good standing.

`ADVERSE_ACCREDITATION_STATUSES` contains only `SUSPENDED` and `EXPIRED` — a
previously held accreditation that has lapsed or been acted against.
`NOT_ACCREDITED` is deliberately excluded.

This is enforced, not just documented:
`tests/test_accreditation_is_voluntary.py` asserts the neutral default, that an
organisation with no accreditation is served normally, and that **no dashboard
figure changes when an accreditation record is deleted** — which would be the
signature of accreditation having crept into a compliance score.

---

## 7. Authentication today, and what has to replace it

**The current identity mechanism is a development shim and is not production
authentication.** The API reads the caller's user id from an `X-User-Id`
header, which is trivially forgeable.

It is contained rather than merely documented:

- It only functions when `auth_mode` is `dev_header`.
- `assert_auth_mode_is_safe()` runs at application startup and **raises**,
  refusing to serve traffic, if `auth_mode` is `dev_header` while `environment`
  is `production`, `prod`, or `staging`.

Replacing it means implementing `resolve_principal` against a verified token
(SSO/SAML/OIDC per the source requirements). **Nothing else changes**: every
other layer consumes `Principal` and `TenantContext`, not headers. The tenancy
tests will keep passing across that swap, because they exercise the layers below
authentication.

---

## 8. How the guarantee is tested

`apps/api/tests/test_security_cross_tenant.py` takes a user who legitimately
belongs to organisation A and tries to reach organisation B by every available
route:

- naming B's organisation id (header **and** `?org=`) on every collection endpoint
- fetching B's record ids while correctly scoped to A
- deleting B's records
- planting a record in B by supplying `organisation_id` in the request body
- parenting an A record to a B record (a foreign key alone cannot express
  "same tenant", so this is checked explicitly)
- reading B's members, or seeing B in the organisation switcher

`test_security_isolation_invariants.py` covers the structural guarantees, and
`test_security_role_enforcement.py` covers permission boundaries within a tenant.

### These tests were verified to actually fail

A security test that passes against a broken system is worse than no test. Both
central controls were deliberately broken to confirm the suite detects it:

| Mutation | Result |
|---|---|
| Tenant filter removed from `TenantScopedRepository._scoped_select()` | **14 tests failed** |
| Membership verification disabled in `resolve_tenant_context()` | **19 tests failed** |

---

## 9. Known gaps

Honest limitations of the current implementation:

1. **No database-level defence in depth.** Isolation is enforced in the
   application, not by PostgreSQL row-level security. A raw SQL query written
   outside the repository layer would not be filtered. RLS (setting a session
   variable per request and adding policies keyed on it) is the natural second
   layer and is not yet implemented.
2. **Authentication is a development shim** (§7).
3. **Member management is read-only.** Roles and permissions are enforced, and
   members are listed, but adding/removing members and changing roles has no
   endpoint yet — `MEMBERS_MANAGE` exists and is enforced, but nothing consumes
   it.
4. **No audit log of tenancy events.** `docs/DOMAIN_MODEL.md` specifies an
   immutable audit trail; membership changes and cross-tenant access attempts
   should write to it once it exists.
5. **Dashboard payloads are still synthetic** and identical for every
   organisation. The routes are correctly tenant-guarded, but the figures are
   fixtures, so they do not yet demonstrate per-tenant data.
6. **Organisation deletion cascades** (`ON DELETE CASCADE`) but there is no
   retention or soft-delete policy, which the source documents require.
