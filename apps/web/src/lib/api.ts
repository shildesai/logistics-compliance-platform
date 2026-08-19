import type {
  Accreditation,
  ApiErrorBody,
  AssignedCoRRole,
  AssignedJurisdiction,
  AssuranceOverview,
  AuditPackDomain,
  BusinessUnit,
  CorrectiveAction,
  CoRRole,
  CurrentUser,
  EvidenceItem,
  Finding,
  Fleet,
  Jurisdiction,
  Membership,
  OrganisationMember,
  OrganisationProfile,
  Site,
  Supplier,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Development identity. There is no login yet: the API accepts the caller's
 * user id from a header, gated so it cannot be used outside development
 * (see apps/api/app/core/security.py). Replaced wholesale by SSO/OIDC. */
export const DEV_USER_ID = process.env.NEXT_PUBLIC_DEV_USER_ID ?? "";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.code = body.error.code;
    this.status = status;
  }
}

interface RequestOptions {
  /** Organisation to act within. Sent as a header and verified server-side
   * against the caller's membership — it is a request, not an authorisation. */
  organisationId?: string;
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { organisationId, method = "GET", body } = options;

  const headers: Record<string, string> = { Accept: "application/json" };
  if (DEV_USER_ID) headers["X-User-Id"] = DEV_USER_ID;
  if (organisationId) headers["X-Organisation-Id"] = organisationId;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      cache: "no-store",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error(`Could not reach the API at ${API_BASE_URL}.`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    const parsed = (await response.json().catch(() => null)) as ApiErrorBody | null;
    if (parsed?.error) {
      throw new ApiError(response.status, parsed);
    }
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Identity
  getMe: () => request<CurrentUser>("/api/v1/me"),
  listMyOrganisations: () => request<Membership[]>("/api/v1/me/organisations"),

  // Organisation profile
  getOrganisation: (org: string) =>
    request<OrganisationProfile>("/api/v1/organisation", { organisationId: org }),
  updateOrganisation: (org: string, body: Partial<OrganisationProfile>) =>
    request<OrganisationProfile>("/api/v1/organisation", {
      organisationId: org,
      method: "PATCH",
      body,
    }),
  listMembers: (org: string) =>
    request<OrganisationMember[]>("/api/v1/organisation/members", { organisationId: org }),

  // Applicability
  listAssignedJurisdictions: (org: string) =>
    request<AssignedJurisdiction[]>("/api/v1/organisation/jurisdictions", {
      organisationId: org,
    }),
  listAvailableJurisdictions: (org: string) =>
    request<Jurisdiction[]>("/api/v1/organisation/jurisdictions/available", {
      organisationId: org,
    }),
  setJurisdictions: (org: string, jurisdictionIds: string[]) =>
    request<AssignedJurisdiction[]>("/api/v1/organisation/jurisdictions", {
      organisationId: org,
      method: "PUT",
      body: { jurisdiction_ids: jurisdictionIds },
    }),

  listAssignedCoRRoles: (org: string) =>
    request<AssignedCoRRole[]>("/api/v1/organisation/cor-roles", { organisationId: org }),
  listAvailableCoRRoles: (org: string) =>
    request<CoRRole[]>("/api/v1/organisation/cor-roles/available", {
      organisationId: org,
    }),
  setCoRRoles: (org: string, corRoleIds: string[]) =>
    request<AssignedCoRRole[]>("/api/v1/organisation/cor-roles", {
      organisationId: org,
      method: "PUT",
      body: { cor_role_ids: corRoleIds },
    }),

  listAccreditations: (org: string) =>
    request<Accreditation[]>("/api/v1/organisation/accreditations", {
      organisationId: org,
    }),

  // Operational records
  listSites: (org: string) => request<Site[]>("/api/v1/sites", { organisationId: org }),
  listFleets: (org: string) => request<Fleet[]>("/api/v1/fleets", { organisationId: org }),
  listSuppliers: (org: string) =>
    request<Supplier[]>("/api/v1/suppliers", { organisationId: org }),
  listBusinessUnits: (org: string) =>
    request<BusinessUnit[]>("/api/v1/business-units", { organisationId: org }),

  // Dashboard
  getOverview: (org: string) =>
    request<AssuranceOverview>("/api/v1/dashboard/overview", { organisationId: org }),
  getEvidence: (org: string) =>
    request<EvidenceItem[]>("/api/v1/dashboard/evidence", { organisationId: org }),
  getFindings: (org: string) =>
    request<Finding[]>("/api/v1/dashboard/findings", { organisationId: org }),
  getCorrectiveActions: (org: string) =>
    request<CorrectiveAction[]>("/api/v1/dashboard/corrective-actions", {
      organisationId: org,
    }),
  getAuditPack: (org: string) =>
    request<AuditPackDomain[]>("/api/v1/dashboard/audit-pack", { organisationId: org }),
};
