"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";
import { Badge } from "@/components/ui/Badge";

export default function FindingsPage() {
  const { data, loading, error } = useOrgData(api.getFindings);

  return (
    <div>
      <PageHeader
        title="Findings"
        description="Potential and confirmed findings with severity, status and confidence. Material findings require human review — see docs/DECISIONS.md §2.5."
      />

      <DataState loading={loading} error={error} empty={data?.length === 0}>
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Finding
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Domain</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Affected entity
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Severity
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Confidence
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((finding) => (
                <tr key={finding.finding_id}>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {finding.finding_id}
                    <span className="ml-2 text-xs text-slate-400">
                      {finding.control_test_id}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{finding.domain}</td>
                  <td className="px-4 py-3 text-slate-600">{finding.affected_entity}</td>
                  <td className="px-4 py-3">
                    <Badge value={finding.severity} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge value={finding.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {Math.round(finding.confidence * 100)}%
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
