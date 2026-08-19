"use client";

import { useState } from "react";

import { useOrg } from "@/contexts/org-context";
import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { DataState } from "@/components/ui/DataState";

export function OrganisationProfileCard() {
  const { can, selectedOrg, reload: reloadOrgs } = useOrg();
  const { data, loading, error, reload } = useOrgData(api.getOrganisation);
  const editable = can("org:manage");

  const [form, setForm] = useState({ name: "", legal_name: "", abn: "" });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Seed the editable form from the loaded record. Adjusting state during
  // render (rather than in an effect) is React's documented pattern for
  // deriving state from changing props, and avoids the extra render pass.
  const [seededFrom, setSeededFrom] = useState<typeof data>(null);
  if (data && data !== seededFrom) {
    setSeededFrom(data);
    setForm({
      name: data.name,
      legal_name: data.legal_name ?? "",
      abn: data.abn ?? "",
    });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedOrg) return;
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      await api.updateOrganisation(selectedOrg.id, {
        name: form.name,
        legal_name: form.legal_name || null,
        abn: form.abn || null,
      });
      setSaved(true);
      reload();
      reloadOrgs();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Could not save changes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="max-w-2xl rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 px-4 py-3">
        <h2 className="font-medium text-slate-900">Organisation profile</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Identifying details for this organisation.
        </p>
      </header>

      <div className="p-4">
        <DataState loading={loading} error={error}>
          {data && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <Field
                label="Trading name"
                value={form.name}
                onChange={(v) => setForm((f) => ({ ...f, name: v }))}
                disabled={!editable}
                required
              />
              <Field
                label="Legal name"
                value={form.legal_name}
                onChange={(v) => setForm((f) => ({ ...f, legal_name: v }))}
                disabled={!editable}
              />
              <Field
                label="ABN"
                value={form.abn}
                onChange={(v) => setForm((f) => ({ ...f, abn: v }))}
                disabled={!editable}
              />

              <dl className="grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 text-sm">
                <div>
                  <dt className="text-slate-500">Identifier</dt>
                  <dd className="font-mono text-xs text-slate-600">{data.slug}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Status</dt>
                  <dd className="text-slate-700 capitalize">{data.status}</dd>
                </div>
              </dl>

              {editable ? (
                <div className="flex items-center gap-3">
                  <button
                    type="submit"
                    disabled={saving}
                    className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                  >
                    {saving ? "Saving…" : "Save changes"}
                  </button>
                  {saved && <span className="text-sm text-emerald-600">Saved</span>}
                  {saveError && <span className="text-sm text-red-600">{saveError}</span>}
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  Your role does not permit editing the organisation profile.
                </p>
              )}
            </form>
          )}
        </DataState>
      </div>
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  disabled,
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      <input
        type="text"
        value={value}
        required={required}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 disabled:bg-slate-50 disabled:text-slate-500"
      />
    </label>
  );
}
