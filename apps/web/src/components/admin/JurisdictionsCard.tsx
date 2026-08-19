"use client";

import { useState } from "react";

import { useOrg } from "@/contexts/org-context";
import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { DataState } from "@/components/ui/DataState";

export function JurisdictionsCard() {
  const { can, selectedOrg } = useOrg();
  const available = useOrgData(api.listAvailableJurisdictions);
  const assigned = useOrgData(api.listAssignedJurisdictions);
  const editable = can("applicability:manage");

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Seed the checkbox selection from what is currently assigned. Adjusting
  // state during render is React's documented pattern for deriving state from
  // changing props; an effect here would cost an extra render pass.
  const [seededFrom, setSeededFrom] = useState<typeof assigned.data>(null);
  if (assigned.data && assigned.data !== seededFrom) {
    setSeededFrom(assigned.data);
    setSelected(new Set(assigned.data.map((a) => a.jurisdiction.id)));
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function save() {
    if (!selectedOrg) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await api.setJurisdictions(selectedOrg.id, [...selected]);
      setMessage("Jurisdictions updated");
      assigned.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 px-4 py-3">
        <h2 className="font-medium text-slate-900">Jurisdictions</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Where this organisation operates. Jurisdiction determines which rule pack
          applies to work performed there.
        </p>
      </header>

      <div className="p-4">
        <DataState
          loading={available.loading || assigned.loading}
          error={available.error ?? assigned.error}
        >
          <ul className="space-y-2">
            {available.data?.map((j) => (
              <li key={j.id}>
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selected.has(j.id)}
                    disabled={!editable}
                    onChange={() => toggle(j.id)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400 disabled:opacity-50"
                  />
                  <span className="text-sm">
                    <span className="font-medium text-slate-800">{j.code}</span>{" "}
                    <span className="text-slate-600">{j.name}</span>
                    {!j.hvnl_participant && (
                      <span
                        className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                        title="Not a Heavy Vehicle National Law participant — operates separate heavy vehicle legislation. Rule packs for this jurisdiction are not yet available."
                      >
                        non-HVNL
                      </span>
                    )}
                  </span>
                </label>
              </li>
            ))}
          </ul>

          {editable ? (
            <div className="mt-4 flex items-center gap-3">
              <button
                type="button"
                onClick={save}
                disabled={saving}
                className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save jurisdictions"}
              </button>
              {message && <span className="text-sm text-emerald-600">{message}</span>}
              {error && <span className="text-sm text-red-600">{error}</span>}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              Your role does not permit changing jurisdictions.
            </p>
          )}
        </DataState>
      </div>
    </section>
  );
}
