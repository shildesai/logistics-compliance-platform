"use client";

import { api } from "@/lib/api";
import { useOrgData } from "@/lib/use-org-data";
import { DataState } from "@/components/ui/DataState";
import {
  ChainStep,
  PsoePills,
  RuleConfigurationView,
  StatusPill,
  TestTypePill,
  VersionBar,
} from "@/components/graph/GraphPrimitives";
import type { ControlDetail, ControlLineage } from "@/lib/types";

export function ControlDetailPanel({
  controlId,
  asAt,
}: {
  controlId: string;
  asAt?: string;
}) {
  // Reuses the shared org-scoped fetch hook (which derives loading state
  // rather than setting it inside an effect), keyed on the control and as-at
  // date so switching either refetches.
  const detail = useOrgData<ControlDetail>(
    (org) => api.inspectControl(org, controlId, asAt),
    [controlId, asAt],
  );
  const lineage = useOrgData<ControlLineage>(
    (org) => api.inspectControlLineage(org, controlId, asAt),
    [controlId, asAt],
  );

  return (
    <div className="space-y-6">
      <DataState
        loading={detail.loading || lineage.loading}
        error={detail.error ?? lineage.error}
      >
        {detail.data && lineage.data && (
          <>
            <ControlSummary detail={detail.data} />
            <LineageChains lineage={lineage.data} detail={detail.data} />
            <TestsAndEvidence detail={detail.data} />
            <VersionHistory lineage={lineage.data} />
          </>
        )}
      </DataState>
    </div>
  );
}

function ControlSummary({ detail }: { detail: ControlDetail }) {
  const version = detail.current_version;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-xs text-slate-500">
            {detail.control.control_code} · {detail.control.domain}
          </p>
          <h2 className="mt-0.5 text-lg font-semibold text-slate-900">
            {version?.name ?? "No version in force on this date"}
          </h2>
        </div>
        {version && <VersionBar meta={version} />}
      </div>

      {version ? (
        <>
          <p className="mt-3 text-sm text-slate-700">{version.objective}</p>
          <dl className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 text-sm sm:grid-cols-4">
            <Field label="Owner" value={version.owner_type.replaceAll("_", " ")} />
            <Field label="Frequency" value={version.frequency.replaceAll("_", " ")} />
            <Field
              label="Automation"
              value={version.automation_level.replaceAll("_", " ")}
            />
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">
                PSOE relevance
              </dt>
              <dd className="mt-1">
                <PsoePills dimensions={version.psoe_relevance} />
              </dd>
            </div>
          </dl>
          {version.change_note && (
            <p className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
              <span className="font-medium">Change note:</span> {version.change_note}
            </p>
          )}
        </>
      ) : (
        <p className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          This control had no version in force on the selected date.
        </p>
      )}
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-1 capitalize text-slate-800">{value.toLowerCase()}</dd>
    </div>
  );
}

function LineageChains({
  lineage,
  detail,
}: {
  lineage: ControlLineage;
  detail: ControlDetail;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-4">
        <h3 className="font-medium text-slate-900">Why this control exists</h3>
        <p className="mt-0.5 text-sm text-slate-500">
          {lineage.paths.length === 1
            ? "The duty this control satisfies."
            : `${lineage.paths.length} obligations are satisfied by this one control — evidence gathered once supports all of them.`}
        </p>
      </header>

      {lineage.paths.length === 0 ? (
        <p className="text-sm text-slate-500">
          No obligation chain was in force on the selected date.
        </p>
      ) : (
        <div className="space-y-6">
          {lineage.paths.map((path) => (
            <div
              key={`${path.obligation.id}-${path.risk.id}`}
              className="space-y-4 rounded-md border border-slate-200 p-4"
            >
              {path.is_primary_control && (
                <span className="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                  primary mitigation
                </span>
              )}

              <ChainStep step="1" label="Regulation" tone="blue">
                <p className="text-sm font-medium text-slate-900">
                  {path.regulation.name}
                </p>
                <p className="text-xs text-slate-500">
                  {path.regulation.regulator}
                  {path.regulation_version &&
                    ` · in force from ${path.regulation_version.effective_from}`}
                </p>
                {path.regulation_version?.jurisdiction_codes?.length ? (
                  <p className="mt-1 text-xs text-slate-500">
                    Applies in: {path.regulation_version.jurisdiction_codes.join(", ")}
                  </p>
                ) : null}
              </ChainStep>

              <ChainStep step="2" label="Obligation" tone="blue">
                <p className="text-sm font-medium text-slate-900">
                  {path.obligation.name}
                </p>
                <p className="mt-0.5 text-sm text-slate-600">
                  {path.obligation.description}
                </p>
                {path.obligation.cor_role_codes.length > 0 && (
                  <p className="mt-1 text-xs text-slate-500">
                    Attaches to:{" "}
                    {path.obligation.cor_role_codes
                      .map((c) => c.replaceAll("_", " ").toLowerCase())
                      .join(", ")}
                  </p>
                )}
                {path.applicability_rules.map((rule) => (
                  <div key={rule.id} className="mt-3">
                    <RuleConfigurationView
                      label={`Applicability — ${rule.name}`}
                      configuration={rule.criteria}
                    />
                  </div>
                ))}
              </ChainStep>

              <ChainStep step="3" label="Risk" tone="amber">
                <p className="text-sm font-medium text-slate-900">{path.risk.name}</p>
                <p className="mt-0.5 text-sm text-slate-600">{path.risk.description}</p>
                {(path.risk.inherent_likelihood || path.risk.inherent_consequence) && (
                  <p className="mt-1 text-xs text-slate-500">
                    Inherent rating:{" "}
                    {path.risk.inherent_likelihood?.toLowerCase()} ×{" "}
                    {path.risk.inherent_consequence?.toLowerCase()}
                  </p>
                )}
              </ChainStep>

              <ChainStep step="4" label="Control" tone="emerald">
                <p className="text-sm font-medium text-slate-900">
                  {detail.current_version?.name ?? detail.control.control_code}
                </p>
                <p className="text-xs text-slate-500">{detail.control.control_code}</p>
              </ChainStep>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function TestsAndEvidence({ detail }: { detail: ControlDetail }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-4">
        <h3 className="font-medium text-slate-900">Tests and evidence</h3>
        <p className="mt-0.5 text-sm text-slate-500">
          How this control is evaluated, and the evidence each test needs in order to
          run.
        </p>
      </header>

      {detail.tests.length === 0 ? (
        <p className="text-sm text-slate-500">No tests defined for this control.</p>
      ) : (
        <div className="space-y-4">
          {detail.tests.map((test) => {
            const version = test.current_version;
            return (
              <div
                key={test.control_test.id}
                className="rounded-md border border-slate-200 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-mono text-xs text-slate-500">
                      {test.control_test.test_code}
                    </p>
                    <p className="text-sm font-medium text-slate-900">
                      {version?.name ?? "No version in force"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {version && <TestTypePill type={version.test_type} />}
                    {version?.human_review_required && (
                      <span
                        title="A person must confirm this result before it becomes a material finding."
                        className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
                      >
                        human review
                      </span>
                    )}
                  </div>
                </div>

                {version && (
                  <>
                    <p className="mt-2 text-sm text-slate-600">
                      {version.test_logic_description}
                    </p>

                    <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
                      <RuleConfigurationView
                        label="Rule configuration"
                        configuration={version.rule_configuration}
                      />
                      <RuleConfigurationView
                        label="Severity configuration"
                        configuration={version.severity_configuration}
                      />
                    </div>

                    <ChainStepEvidence test={test} />

                    {test.remediation_templates.length > 0 && (
                      <div className="mt-4">
                        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                          Remediation
                        </p>
                        {test.remediation_templates.map((template) => (
                          <div
                            key={template.id}
                            className="rounded-md border border-slate-200 bg-slate-50/60 p-3"
                          >
                            <p className="text-sm font-medium text-slate-800">
                              {template.title}
                            </p>
                            <p className="mt-0.5 text-xs text-slate-600">
                              {template.description}
                            </p>
                            <ol className="mt-2 list-decimal space-y-0.5 pl-5 text-xs text-slate-600">
                              {template.suggested_steps.map((step) => (
                                <li key={step}>{step}</li>
                              ))}
                            </ol>
                            <p className="mt-2 text-xs text-slate-500">
                              Default owner:{" "}
                              {template.default_owner_type
                                .replaceAll("_", " ")
                                .toLowerCase()}{" "}
                              · due in {template.default_due_days} days
                              {template.requires_closure_evidence &&
                                " · closure evidence required"}
                              {template.requires_effectiveness_check &&
                                " · effectiveness re-checked"}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function ChainStepEvidence({
  test,
}: {
  test: ControlDetail["tests"][number];
}) {
  if (test.evidence_requirements.length === 0) {
    return null;
  }
  return (
    <div className="mt-4">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
        Evidence required
      </p>
      <ul className="divide-y divide-slate-100 rounded-md border border-slate-200">
        {test.evidence_requirements.map((requirement) => (
          <li key={requirement.id} className="px-3 py-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium text-slate-800">
                {requirement.name}
              </span>
              <span className="flex items-center gap-2 text-xs">
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-600">
                  {requirement.source_type.replaceAll("_", " ").toLowerCase()}
                </span>
                {requirement.is_mandatory ? (
                  <span className="text-slate-500">mandatory</span>
                ) : (
                  <span className="text-slate-400">optional</span>
                )}
              </span>
            </div>
            <p className="mt-1 font-mono text-[11px] text-slate-500">
              {requirement.required_fields.join(", ")}
            </p>
            {requirement.max_age_days !== null && (
              <p className="text-[11px] text-slate-500">
                Must be no older than {requirement.max_age_days} day
                {requirement.max_age_days === 1 ? "" : "s"}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function VersionHistory({ lineage }: { lineage: ControlLineage }) {
  if (lineage.control_version_history.length <= 1) {
    return null;
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3">
        <h3 className="font-medium text-slate-900">Version history</h3>
        <p className="mt-0.5 text-sm text-slate-500">
          Superseded versions are kept so a past assessment can still be read against
          the rule that applied at the time.
        </p>
      </header>
      <ul className="divide-y divide-slate-100">
        {lineage.control_version_history.map((version) => (
          <li key={version.id} className="py-2">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-medium text-slate-800">v{version.version}</span>
              <StatusPill status={version.status} />
              <span className="text-xs text-slate-500">
                {version.effective_from} →{" "}
                {version.effective_to ?? "current"}
              </span>
            </div>
            {version.change_note && (
              <p className="mt-1 text-xs text-slate-600">{version.change_note}</p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
