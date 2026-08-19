"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";
import { ControlDetailPanel } from "@/components/graph/ControlDetailPanel";
import type { ControlListItem } from "@/lib/types";

export default function ControlExplorerPage() {
  const [selectedControlId, setSelectedControlId] = useState<string | null>(null);
  const [asAt, setAsAt] = useState<string>("");

  // `asAt` is a dependency: changing the date must re-resolve which versions
  // are in force, not just re-render the current ones.
  const controls = useOrgData<ControlListItem[]>(
    (org) => api.browseControls(org, { asAt: asAt || undefined }),
    [asAt],
  );
  const stats = useOrgData(
    (org) => api.getGraphStatistics(org, asAt || undefined),
    [asAt],
  );

  return (
    <div>
      <PageHeader
        title="Control Explorer"
        description="Trace each control back to the duty it exists to satisfy: Regulation → Obligation → Risk → Control → Evidence → Tests."
      />

      <div className="mb-6 flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label className="block">
          <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
            View the graph as at
          </span>
          <input
            type="date"
            value={asAt}
            onChange={(e) => setAsAt(e.target.value)}
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400"
          />
        </label>
        {asAt && (
          <button
            type="button"
            onClick={() => setAsAt("")}
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Back to today
          </button>
        )}
        <p className="max-w-md text-xs text-slate-500">
          Regulatory content is effective-dated. Setting a past date shows the rules
          that actually applied then, which is how a historical assessment stays
          reproducible.
        </p>

        {stats.data && (
          <dl className="ml-auto flex gap-6 text-sm">
            {[
              ["Regulations", stats.data.regulations],
              ["Obligations", stats.data.obligations],
              ["Controls", stats.data.controls],
              ["Tests", stats.data.control_tests],
            ].map(([label, value]) => (
              <div key={label as string}>
                <dt className="text-xs uppercase tracking-wide text-slate-400">
                  {label}
                </dt>
                <dd className="font-semibold text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[22rem_1fr]">
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <header className="border-b border-slate-200 px-4 py-3">
            <h2 className="font-medium text-slate-900">Controls</h2>
          </header>
          <div className="p-2">
            <DataState
              loading={controls.loading}
              error={controls.error}
              empty={controls.data?.length === 0}
            >
              <ul className="space-y-1">
                {controls.data?.map((item) => {
                  const isSelected = item.control.id === selectedControlId;
                  return (
                    <li key={item.control.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedControlId(item.control.id)}
                        aria-current={isSelected ? "true" : undefined}
                        className={`w-full rounded-md px-3 py-2 text-left transition-colors ${
                          isSelected ? "bg-slate-900 text-white" : "hover:bg-slate-50"
                        }`}
                      >
                        <span className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs opacity-80">
                            {item.control.control_code}
                          </span>
                          {item.current_version && (
                            <span className="text-xs opacity-70">
                              v{item.current_version.version}
                            </span>
                          )}
                        </span>
                        <span className="mt-0.5 block text-sm font-medium">
                          {item.current_version?.name ?? (
                            <span className="italic opacity-70">
                              No version in force
                            </span>
                          )}
                        </span>
                        <span
                          className={`mt-0.5 block text-xs ${
                            isSelected ? "text-slate-300" : "text-slate-500"
                          }`}
                        >
                          {item.control.domain}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </DataState>
          </div>
        </section>

        <section>
          {selectedControlId ? (
            <ControlDetailPanel controlId={selectedControlId} asAt={asAt || undefined} />
          ) : (
            <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
              Select a control to trace it back to the regulation it satisfies.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
