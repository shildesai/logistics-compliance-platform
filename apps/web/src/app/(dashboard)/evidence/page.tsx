"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";
import { Badge } from "@/components/ui/Badge";

export default function EvidencePage() {
  const { data, loading, error } = useOrgData(api.getEvidence);

  return (
    <div>
      <PageHeader
        title="Evidence"
        description="Source evidence with lineage: source system, entity linkage, capture time and test result."
      />

      <DataState loading={loading} error={error} empty={data?.length === 0}>
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Evidence ID
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Source system
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Entity</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Control test
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Captured at
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((item) => (
                <tr key={item.evidence_id}>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {item.evidence_id}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{item.source_system}</td>
                  <td className="px-4 py-3 text-slate-600">{item.entity}</td>
                  <td className="px-4 py-3 text-slate-600">{item.control_test_id}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                    {new Date(item.captured_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <Badge value={item.status} />
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
