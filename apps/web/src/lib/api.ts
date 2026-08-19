import type {
  ApiErrorBody,
  AssuranceOverview,
  AuditPackDomain,
  CorrectiveAction,
  EvidenceItem,
  Finding,
  Organization,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }

  const response = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    if (body?.error) {
      throw new ApiError(response.status, body);
    }
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  listOrganizations: () => apiGet<Organization[]>("/api/v1/organizations"),
  getOverview: (org: string) =>
    apiGet<AssuranceOverview>("/api/v1/dashboard/overview", { org }),
  getEvidence: (org: string) =>
    apiGet<EvidenceItem[]>("/api/v1/dashboard/evidence", { org }),
  getFindings: (org: string) => apiGet<Finding[]>("/api/v1/dashboard/findings", { org }),
  getCorrectiveActions: (org: string) =>
    apiGet<CorrectiveAction[]>("/api/v1/dashboard/corrective-actions", { org }),
  getAuditPack: (org: string) =>
    apiGet<AuditPackDomain[]>("/api/v1/dashboard/audit-pack", { org }),
};
