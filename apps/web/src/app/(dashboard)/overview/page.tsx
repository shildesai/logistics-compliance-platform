"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { DataState } from "@/components/ui/DataState";

export default function OverviewPage() {
  const { data, loading, error } = useOrgData(api.getOverview);

  return (
    <div>
      <PageHeader
        title="Assurance Overview"
        description="PSOE status by control domain, high-risk findings, overdue corrective actions and evidence freshness."
      />

      <DataState loading={loading} error={error}>
        {data && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatCard
                label="High-risk findings"
                value={data.high_risk_findings}
                tone={data.high_risk_findings > 0 ? "critical" : "positive"}
              />
              <StatCard
                label="Overdue corrective actions"
                value={data.overdue_corrective_actions}
                tone={data.overdue_corrective_actions > 0 ? "warning" : "positive"}
              />
              <StatCard
                label="Evidence freshness"
                value={`${data.evidence_freshness_pct}%`}
                tone="positive"
              />
            </div>

            <div className="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">
                      Domain
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">
                      Controls
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">
                      Open findings
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">
                      Present
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">
                      Suitable
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">
                      Operating
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">
                      Effective
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.domains.map((domain) => (
                    <tr key={domain.domain}>
                      <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                        {domain.domain}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{domain.control_count}</td>
                      <td className="px-4 py-3 text-slate-600">{domain.open_findings}</td>
                      <td className="px-4 py-3 text-slate-600">{domain.psoe.present}%</td>
                      <td className="px-4 py-3 text-slate-600">{domain.psoe.suitable}%</td>
                      <td className="px-4 py-3 text-slate-600">{domain.psoe.operating}%</td>
                      <td className="px-4 py-3 text-slate-600">{domain.psoe.effective}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Generated {new Date(data.generated_at).toLocaleString()} &middot; synthetic
              data (Phase 1 shell)
            </p>
          </>
        )}
      </DataState>
    </div>
  );
}
