"use client";

import { useOrg } from "@/contexts/org-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";

export default function AdministrationPage() {
  const { organizations, selectedOrg, loading, error } = useOrg();

  return (
    <div>
      <PageHeader
        title="Administration"
        description="Organisation, users and connector configuration. Full RBAC/ABAC, SSO and connector management are Phase 0 follow-up work, not this shell."
      />

      <DataState loading={loading} error={error}>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-medium text-slate-900">Organisations</h3>
            <ul className="mt-3 divide-y divide-slate-100 text-sm">
              {organizations.map((org) => (
                <li key={org.id} className="flex items-center justify-between py-2">
                  <span className="text-slate-700">{org.name}</span>
                  {org.slug === selectedOrg?.slug && (
                    <span className="text-xs font-medium text-slate-400">selected</span>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-medium text-slate-900">Data connectors</h3>
            <ul className="mt-3 divide-y divide-slate-100 text-sm text-slate-600">
              <li className="py-2">TMS — not connected</li>
              <li className="py-2">EWD / work diary — not connected</li>
              <li className="py-2">Telematics / GPS — not connected</li>
              <li className="py-2">Fleet maintenance — not connected</li>
              <li className="py-2">CSV / Excel upload — available</li>
            </ul>
          </div>
        </div>
      </DataState>
    </div>
  );
}
