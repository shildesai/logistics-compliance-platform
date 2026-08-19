"use client";

import type {
  ControlTestType,
  LifecycleStatus,
  PsoeDimension,
  VersionMeta,
} from "@/lib/types";

const STATUS_STYLES: Record<LifecycleStatus, string> = {
  ACTIVE: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  SUPERSEDED: "bg-slate-100 text-slate-600 ring-slate-500/20",
  RETIRED: "bg-slate-100 text-slate-600 ring-slate-500/20",
  DRAFT: "bg-blue-50 text-blue-700 ring-blue-600/20",
  IN_REVIEW: "bg-amber-50 text-amber-700 ring-amber-600/20",
  APPROVED: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
};

const TEST_TYPE_STYLES: Record<ControlTestType, string> = {
  DETERMINISTIC: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  ANALYTICAL: "bg-blue-50 text-blue-700 ring-blue-600/20",
  // AI-assisted results are always potential findings pending human review.
  AI_ASSISTED: "bg-violet-50 text-violet-700 ring-violet-600/20",
  MANUAL: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

export function StatusPill({ status }: { status: LifecycleStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[status]}`}
    >
      {status.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}

export function TestTypePill({ type }: { type: ControlTestType }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TEST_TYPE_STYLES[type]}`}
    >
      {type.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}

export function PsoePills({ dimensions }: { dimensions: PsoeDimension[] }) {
  if (dimensions.length === 0) {
    return <span className="text-xs text-slate-400">—</span>;
  }
  return (
    <span className="flex flex-wrap gap-1">
      {dimensions.map((d) => (
        <span
          key={d}
          title={`PSOE dimension: ${d.toLowerCase()}`}
          className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-600"
        >
          {d.slice(0, 1)}
        </span>
      ))}
    </span>
  );
}

/** The governance envelope: version, status, effective window, source. */
export function VersionBar({ meta }: { meta: VersionMeta }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
      <span className="font-medium text-slate-700">v{meta.version}</span>
      <StatusPill status={meta.status} />
      <span>
        In force {meta.effective_from}
        {meta.effective_to ? ` → ${meta.effective_to}` : " → current"}
      </span>
      {meta.source_reference && (
        <span className="truncate" title={meta.source_reference}>
          Source: {meta.source_reference}
        </span>
      )}
    </div>
  );
}

/**
 * Renders versioned rule configuration as inert, read-only data.
 *
 * This component deliberately does not interpret what it is given. Thresholds,
 * comparisons and jurisdiction lists are regulatory logic; they are evaluated
 * server-side and displayed here only so a reviewer can read what was
 * configured. Adding a branch on these values would put legal logic into the
 * frontend, which CLAUDE.md forbids and which would escape versioning and
 * approval entirely.
 */
export function RuleConfigurationView({
  label,
  configuration,
}: {
  label: string;
  configuration: Record<string, unknown>;
}) {
  const entries = Object.entries(configuration);
  if (entries.length === 0) {
    return null;
  }

  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <dl className="divide-y divide-slate-100 rounded-md border border-slate-200 bg-slate-50/60 text-xs">
        {entries.map(([key, value]) => (
          <div key={key} className="flex gap-3 px-3 py-1.5">
            <dt className="w-44 shrink-0 font-mono text-slate-500">{key}</dt>
            <dd className="min-w-0 flex-1 break-words font-mono text-slate-800">
              {typeof value === "object" && value !== null
                ? JSON.stringify(value)
                : String(value)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function ChainStep({
  step,
  label,
  children,
  tone = "slate",
}: {
  step: string;
  label: string;
  children: React.ReactNode;
  tone?: "slate" | "amber" | "emerald" | "blue" | "violet";
}) {
  const tones: Record<string, string> = {
    slate: "border-slate-300 bg-slate-50 text-slate-700",
    amber: "border-amber-300 bg-amber-50 text-amber-800",
    emerald: "border-emerald-300 bg-emerald-50 text-emerald-800",
    blue: "border-blue-300 bg-blue-50 text-blue-800",
    violet: "border-violet-300 bg-violet-50 text-violet-800",
  };

  return (
    <div className="relative pl-8">
      <span
        className={`absolute left-0 top-0.5 flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-semibold ${tones[tone]}`}
      >
        {step}
      </span>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <div className="mt-1">{children}</div>
    </div>
  );
}
