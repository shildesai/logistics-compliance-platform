"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { DataState } from "@/components/ui/DataState";
import type { AccreditationStatus } from "@/lib/types";

/** Presentation for each status.
 *
 * NOT_ACCREDITED is styled neutrally, exactly like any other informational
 * value — accreditation is voluntary, so choosing not to hold it is not a
 * deficiency and must never be rendered as a warning. Only SUSPENDED and
 * EXPIRED (a previously held accreditation that has lapsed or been acted
 * against) get attention styling. See apps/api/app/models/accreditation.py.
 */
const STATUS_STYLES: Record<AccreditationStatus, string> = {
  ACCREDITED: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  APPLIED: "bg-blue-50 text-blue-700 ring-blue-600/20",
  NOT_ACCREDITED: "bg-slate-50 text-slate-600 ring-slate-500/20",
  WITHDRAWN: "bg-slate-50 text-slate-600 ring-slate-500/20",
  SUSPENDED: "bg-amber-50 text-amber-700 ring-amber-600/20",
  EXPIRED: "bg-amber-50 text-amber-700 ring-amber-600/20",
};

function StatusBadge({ status }: { status: AccreditationStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[status]}`}
    >
      {status.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}

export function AccreditationCard() {
  const { data, loading, error } = useOrgData(api.listAccreditations);

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 px-4 py-3">
        <h2 className="font-medium text-slate-900">Accreditation</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Heavy vehicle accreditation is a <strong>voluntary</strong> scheme for eligible
          operators. It is not required in order to operate, and Chain of Responsibility
          duties apply either way. Records here are for your own reference.
        </p>
      </header>

      <div className="p-4">
        <DataState loading={loading} error={error}>
          {data && data.length === 0 ? (
            // Neutral empty state — deliberately not a warning or a gap.
            <p className="rounded-md bg-slate-50 px-4 py-6 text-center text-sm text-slate-600">
              No accreditation recorded. Accreditation is voluntary, so nothing is
              required here.
            </p>
          ) : (
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr>
                  <th className="px-2 py-2 text-left font-medium text-slate-500">Scheme</th>
                  <th className="px-2 py-2 text-left font-medium text-slate-500">Module</th>
                  <th className="px-2 py-2 text-left font-medium text-slate-500">Status</th>
                  <th className="px-2 py-2 text-left font-medium text-slate-500">Number</th>
                  <th className="px-2 py-2 text-left font-medium text-slate-500">
                    Valid to
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.map((record) => (
                  <tr key={record.id}>
                    <td className="px-2 py-2 font-medium text-slate-900">
                      {record.scheme}
                    </td>
                    <td className="px-2 py-2 text-slate-600">
                      {record.module.replaceAll("_", " ").toLowerCase()}
                    </td>
                    <td className="px-2 py-2">
                      <StatusBadge status={record.status} />
                    </td>
                    <td className="px-2 py-2 font-mono text-xs text-slate-600">
                      {record.accreditation_number ?? "—"}
                    </td>
                    <td className="px-2 py-2 text-slate-600">{record.valid_to ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </DataState>
      </div>
    </section>
  );
}
