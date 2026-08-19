const TONE_CLASSES: Record<string, string> = {
  critical: "bg-red-50 text-red-700 ring-red-600/20",
  high: "bg-amber-50 text-amber-700 ring-amber-600/20",
  medium: "bg-blue-50 text-blue-700 ring-blue-600/20",
  low: "bg-slate-50 text-slate-600 ring-slate-500/20",
  confirmed: "bg-red-50 text-red-700 ring-red-600/20",
  potential: "bg-amber-50 text-amber-700 ring-amber-600/20",
  overdue: "bg-red-50 text-red-700 ring-red-600/20",
  in_progress: "bg-blue-50 text-blue-700 ring-blue-600/20",
  not_started: "bg-slate-50 text-slate-600 ring-slate-500/20",
  ready: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  processed: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  pending_review: "bg-amber-50 text-amber-700 ring-amber-600/20",
};

export function Badge({ value }: { value: string }) {
  const key = value.toLowerCase();
  const classes = TONE_CLASSES[key] ?? "bg-slate-50 text-slate-600 ring-slate-500/20";
  const label = value.replaceAll("_", " ");

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${classes}`}
    >
      {label}
    </span>
  );
}
