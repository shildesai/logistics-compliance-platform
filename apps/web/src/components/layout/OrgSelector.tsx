"use client";

import { useOrg } from "@/contexts/org-context";

export function OrgSelector() {
  const { organizations, selectedOrg, setSelectedOrgSlug, loading } = useOrg();

  if (loading) {
    return <div className="h-9 w-48 animate-pulse rounded-md bg-slate-100" />;
  }

  if (!selectedOrg) {
    return <span className="text-sm text-slate-400">No organisation available</span>;
  }

  return (
    <label className="flex items-center gap-2">
      <span className="sr-only">Organisation</span>
      <select
        value={selectedOrg.slug}
        onChange={(e) => setSelectedOrgSlug(e.target.value)}
        className="min-w-[10rem] rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400"
      >
        {organizations.map((org) => (
          <option key={org.slug} value={org.slug}>
            {org.name}
          </option>
        ))}
      </select>
    </label>
  );
}
