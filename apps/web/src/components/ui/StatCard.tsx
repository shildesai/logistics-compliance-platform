export function StatCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  tone?: "neutral" | "warning" | "critical" | "positive";
}) {
  const toneClasses: Record<string, string> = {
    neutral: "text-slate-900",
    warning: "text-amber-600",
    critical: "text-red-600",
    positive: "text-emerald-600",
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${toneClasses[tone]}`}>{value}</p>
    </div>
  );
}
