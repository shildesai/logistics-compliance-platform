"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";
import { Badge } from "@/components/ui/Badge";

export default function AuditReadinessPage() {
  const { data, loading, error } = useOrgData(api.getAuditPack);

  return (
    <div>
      <PageHeader
        title="Audit Readiness"
        description="Lightweight audit-pack export by domain. Full sampling, evidence requests and auditor collaboration are Phase 2 (see docs/IMPLEMENTATION_PLAN.md §7)."
      />

      <DataState loading={loading} error={error} empty={data?.length === 0}>
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Domain</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Population
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Exceptions
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((domain) => (
                <tr key={domain.domain}>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {domain.domain}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{domain.population}</td>
                  <td className="px-4 py-3 text-slate-600">{domain.exceptions}</td>
                  <td className="px-4 py-3">
                    <Badge value={domain.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataState>
    </div>
  );
}
