import { PageHeader } from "@/components/ui/PageHeader";

export default function ComplianceAssistantPage() {
  return (
    <div>
      <PageHeader
        title="Compliance Assistant"
        description="Grounded natural-language Q&A over controls, evidence, findings and suppliers."
      />

      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-600">
        <p className="font-medium text-slate-900">Not enabled in this phase.</p>
        <p className="mt-2">
          The Compliance Assistant is gated behind a dedicated grounding and evaluation
          pass (Phase 1.5) before it is exposed to users, per{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">
            docs/DECISIONS.md
          </code>{" "}
          §1.8: it must never fabricate an answer outside permitted evidence, and it can
          never confirm a compliance finding on its own.
        </p>
      </div>
    </div>
  );
}
