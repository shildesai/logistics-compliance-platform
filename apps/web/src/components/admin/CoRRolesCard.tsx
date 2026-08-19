"use client";

import { useState } from "react";

import { useOrg } from "@/contexts/org-context";
import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { DataState } from "@/components/ui/DataState";

export function CoRRolesCard() {
  const { can, selectedOrg } = useOrg();
  const available = useOrgData(api.listAvailableCoRRoles);
  const assigned = useOrgData(api.listAssignedCoRRoles);
  const editable = can("applicability:manage");

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // See JurisdictionsCard: state derived during render rather than in an effect.
  const [seededFrom, setSeededFrom] = useState<typeof assigned.data>(null);
  if (assigned.data && assigned.data !== seededFrom) {
    setSeededFrom(assigned.data);
    setSelected(new Set(assigned.data.map((a) => a.cor_role.id)));
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
      await api.setCoRRoles(selectedOrg.id, [...selected]);
      setMessage("Chain of Responsibility roles updated");
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
        <h2 className="font-medium text-slate-900">Chain of Responsibility roles</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          CoR duties attach to what a business does, so more than one role can apply at
          once. This records your own determination — the platform does not make the
          legal assessment for you.
        </p>
      </header>

      <div className="p-4">
        <DataState
          loading={available.loading || assigned.loading}
          error={available.error ?? assigned.error}
        >
          <ul className="space-y-3">
            {available.data?.map((role) => (
              <li key={role.id}>
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selected.has(role.id)}
                    disabled={!editable}
                    onChange={() => toggle(role.id)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400 disabled:opacity-50"
                  />
                  <span className="text-sm">
                    <span className="font-medium text-slate-800">{role.name}</span>
                    {role.description && (
                      <span className="mt-0.5 block text-xs text-slate-500">
                        {role.description}
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
                {saving ? "Saving…" : "Save CoR roles"}
              </button>
              {message && <span className="text-sm text-emerald-600">{message}</span>}
              {error && <span className="text-sm text-red-600">{error}</span>}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              Your role does not permit changing CoR roles.
            </p>
          )}
        </DataState>
      </div>
    </section>
  );
}
