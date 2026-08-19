"use client";

import { useState } from "react";

import { useOrg } from "@/contexts/org-context";
import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";
import { Badge } from "@/components/ui/Badge";
import { OrganisationProfileCard } from "@/components/admin/OrganisationProfileCard";
import { JurisdictionsCard } from "@/components/admin/JurisdictionsCard";
import { CoRRolesCard } from "@/components/admin/CoRRolesCard";
import { AccreditationCard } from "@/components/admin/AccreditationCard";

type Tab = "profile" | "applicability" | "members" | "operations";

const TABS: { id: Tab; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "applicability", label: "Applicability" },
  { id: "members", label: "Members" },
  { id: "operations", label: "Operations" },
];

export default function AdministrationPage() {
  const [tab, setTab] = useState<Tab>("profile");
  const { selectedOrg, loading, error } = useOrg();

  return (
    <div>
      <PageHeader
        title="Administration"
        description="Organisation profile, the jurisdictions and Chain of Responsibility roles that determine which obligations apply, members, and operational records."
      />

      <DataState loading={loading} error={error}>
        {selectedOrg && (
          <>
            <div className="mb-6 border-b border-slate-200">
              <nav className="-mb-px flex gap-6" aria-label="Administration sections">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTab(t.id)}
                    aria-current={tab === t.id ? "page" : undefined}
                    className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                      tab === t.id
                        ? "border-slate-900 text-slate-900"
                        : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </nav>
            </div>

            {tab === "profile" && <OrganisationProfileCard />}
            {tab === "applicability" && (
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <JurisdictionsCard />
                <CoRRolesCard />
                <div className="xl:col-span-2">
                  <AccreditationCard />
                </div>
              </div>
            )}
            {tab === "members" && <MembersCard />}
            {tab === "operations" && <OperationsCards />}
          </>
        )}
      </DataState>
    </div>
  );
}

function MembersCard() {
  const { data, loading, error } = useOrgData(api.listMembers);

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 px-4 py-3">
        <h2 className="font-medium text-slate-900">Members</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          People with access to this organisation, and the role each holds.
        </p>
      </header>
      <div className="p-4">
        <DataState loading={loading} error={error} empty={data?.length === 0}>
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead>
              <tr>
                <th className="px-2 py-2 text-left font-medium text-slate-500">Name</th>
                <th className="px-2 py-2 text-left font-medium text-slate-500">Email</th>
                <th className="px-2 py-2 text-left font-medium text-slate-500">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((member) => (
                <tr key={member.user_id}>
                  <td className="px-2 py-2 font-medium text-slate-900">
                    {member.full_name}
                  </td>
                  <td className="px-2 py-2 text-slate-600">{member.email}</td>
                  <td className="px-2 py-2">
                    <Badge value={member.role.replaceAll("_", " ").toLowerCase()} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataState>
      </div>
    </section>
  );
}

function OperationsCards() {
  const sites = useOrgData(api.listSites);
  const fleets = useOrgData(api.listFleets);
  const suppliers = useOrgData(api.listSuppliers);
  const businessUnits = useOrgData(api.listBusinessUnits);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <SimpleListCard
        title="Business units"
        description="Divisions within this organisation."
        state={businessUnits}
        render={(bu) => (
          <li key={bu.id} className="flex justify-between py-2">
            <span className="text-slate-700">{bu.name}</span>
            <span className="text-xs text-slate-400">{bu.code}</span>
          </li>
        )}
      />
      <SimpleListCard
        title="Sites"
        description="Physical locations this organisation operates from or into."
        state={sites}
        render={(site) => (
          <li key={site.id} className="flex justify-between py-2">
            <span className="text-slate-700">
              {site.name}
              {site.suburb && <span className="text-slate-400"> · {site.suburb}</span>}
            </span>
            <span className="text-xs text-slate-400">{site.code}</span>
          </li>
        )}
      />
      <SimpleListCard
        title="Fleets"
        description="Vehicle groupings. Individual vehicles live in the fleet system, not here."
        state={fleets}
        render={(fleet) => (
          <li key={fleet.id} className="flex justify-between py-2">
            <span className="text-slate-700">{fleet.name}</span>
            <span className="text-xs text-slate-400">{fleet.vehicle_count} vehicles</span>
          </li>
        )}
      />
      <SimpleListCard
        title="Suppliers"
        description="Transport suppliers engaged by this organisation."
        state={suppliers}
        render={(supplier) => (
          <li key={supplier.id} className="flex justify-between py-2">
            <span className="text-slate-700">{supplier.name}</span>
            <span className="text-xs text-slate-400">
              {supplier.supplier_type.replaceAll("_", " ").toLowerCase()}
            </span>
          </li>
        )}
      />
    </div>
  );
}

function SimpleListCard<T>({
  title,
  description,
  state,
  render,
}: {
  title: string;
  description: string;
  state: { data: T[] | null; loading: boolean; error: string | null };
  render: (item: T) => React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-medium text-slate-900">{title}</h2>
      <p className="mt-0.5 text-sm text-slate-500">{description}</p>
      <div className="mt-3">
        <DataState
          loading={state.loading}
          error={state.error}
          empty={state.data?.length === 0}
        >
          <ul className="divide-y divide-slate-100 text-sm">
            {state.data?.map(render)}
          </ul>
        </DataState>
      </div>
    </section>
  );
}
