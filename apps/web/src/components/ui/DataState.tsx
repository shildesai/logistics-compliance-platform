import type { ReactNode } from "react";

export function DataState({
  loading,
  error,
  empty,
  children,
}: {
  loading: boolean;
  error: string | null;
  empty?: boolean;
  children: ReactNode;
}) {
  if (loading) {
    return (
      <div
        role="status"
        className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500"
      >
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
      >
        <p className="font-medium">Couldn&apos;t load this data.</p>
        <p className="mt-1 text-red-600">{error}</p>
        <p className="mt-2 text-xs text-red-500">
          Is the API running at{" "}
          {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}?
        </p>
      </div>
    );
  }

  if (empty) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        Nothing to show yet.
      </div>
    );
  }

  return <>{children}</>;
}
