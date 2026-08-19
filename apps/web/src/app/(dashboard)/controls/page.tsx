"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";

export default function ControlsPage() {
  const { data, loading, error } = useOrgData(api.getOverview);

  return (
    <div>
      <PageHeader
        title="Controls"
        description="Control catalogue by domain: Regulation → Obligation → Risk → Control → Evidence → Tests → Findings. See docs/DOMAIN_MODEL.md for the full control-catalogue context."
      />

      <DataState loading={loading} error={error}>
        {data && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.domains.map((domain) => (
              <div
                key={domain.domain}
                className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
              >
                <h3 className="font-medium text-slate-900">{domain.domain}</h3>
                <dl className="mt-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Control tests</dt>
                    <dd className="font-medium text-slate-900">{domain.control_count}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Open findings</dt>
                    <dd className="font-medium text-slate-900">{domain.open_findings}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Effective</dt>
                    <dd className="font-medium text-slate-900">{domain.psoe.effective}%</dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        )}
      </DataState>
    </div>
  );
}
