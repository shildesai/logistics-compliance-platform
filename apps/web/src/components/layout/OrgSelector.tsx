"use client";

import { useOrg } from "@/contexts/org-context";

export function OrgSelector() {
  const { memberships, selectedOrg, selectedMembership, setSelectedOrgId, loading } =
    useOrg();

  if (loading) {
    return <div className="h-9 w-48 animate-pulse rounded-md bg-slate-100" />;
  }

  if (!selectedOrg) {
    return <span className="text-sm text-slate-400">No organisation available</span>;
  }

  return (
    <div className="flex items-center gap-2">
      <label className="flex items-center gap-2">
        <span className="sr-only">Organisation</span>
        <select
          value={selectedOrg.id}
          onChange={(e) => setSelectedOrgId(e.target.value)}
          className="min-w-[12rem] rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          {memberships.map((m) => (
            <option key={m.organisation.id} value={m.organisation.id}>
              {m.organisation.name}
            </option>
          ))}
        </select>
      </label>
      {selectedMembership && (
        <span
          title="Your role in this organisation"
          className="hidden rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 sm:inline"
        >
          {selectedMembership.role.replaceAll("_", " ")}
        </span>
      )}
    </div>
  );
}
