"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataState } from "@/components/ui/DataState";
import { Badge } from "@/components/ui/Badge";

export default function CorrectiveActionsPage() {
  const { data, loading, error } = useOrgData(api.getCorrectiveActions);

  return (
    <div>
      <PageHeader
        title="Corrective Actions"
        description="Owner, due date, remediation status and closure evidence for each corrective action request (CAR)."
      />

      <DataState loading={loading} error={error} empty={data?.length === 0}>
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-500">CAR</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Linked finding
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Owner</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">
                  Due date
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((car) => (
                <tr key={car.car_id}>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                    {car.car_id}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{car.finding_id}</td>
                  <td className="px-4 py-3 text-slate-600">{car.owner}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                    {car.due_date}
                  </td>
                  <td className="px-4 py-3">
                    <Badge value={car.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataState>
    </div>
  );
}
