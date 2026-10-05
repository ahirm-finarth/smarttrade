"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Play, RefreshCw } from "lucide-react";
import { DataTable, EmptyState, SectionHeading } from "@/components/ui";
import { readable } from "@/components/document-status";
import { evidenceValue } from "@/components/examination-workspace";
import { getRiskRun, getRiskRuns, runRiskChecks } from "@/lib/api";
import { dateTime } from "@/lib/format";
import type { RiskDetail, RiskRun, ProviderCheck } from "@/types/risk";
import type { Evidence } from "@/types/examinations";

const categories = [
  "screening",
  "country",
  "port",
  "vessel",
  "duplicate",
  "goods",
  "fair_value",
];
function RiskStatus({ value }: { value: string }) {
  const kind =
    value === "CLEAR"
      ? "result-matched"
      : value === "PROVIDER_ERROR" || value === "FAILED" || value === "HIT"
        ? "result-finding"
        : value === "POTENTIAL_MATCH" ||
            value === "NEEDS_REVIEW" ||
            value === "PARTIAL" ||
            value === "INSUFFICIENT_DATA"
          ? "result-review"
          : "outcome-neutral";
  return (
    <span className={`examination-result ${kind}`}>{readable(value)}</span>
  );
}
function sourceURL(e: Evidence) {
  return `/documents/${e.document_id}?version_id=${e.document_version_id}&run_id=${e.processing_run_id}&fact_id=${e.fact_id}#source-page`;
}
function aggregate(checks: ProviderCheck[]) {
  return (
    [
      "PROVIDER_ERROR",
      "INSUFFICIENT_DATA",
      "HIT",
      "POTENTIAL_MATCH",
      "NEEDS_REVIEW",
      "NOT_CHECKED",
      "CLEAR",
      "NOT_APPLICABLE",
    ].find((s) => checks.some((c) => c.status === s)) || "NOT_CHECKED"
  );
}
function firstCheck(data: RiskDetail) {
  return (
    data.findings[0]?.provider_check_pk ??
    data.checks.find(
      (c) => c.status !== "CLEAR" && c.status !== "NOT_APPLICABLE",
    )?.id ??
    data.checks[0]?.id ??
    null
  );
}

export function RiskWorkspace({
  caseId,
  active,
}: {
  caseId: string;
  active: boolean;
}) {
  const [history, setHistory] = useState<RiskRun[]>([]);
  const [data, setData] = useState<RiskDetail | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const requestId = useRef<string | null>(null);
  const refresh = useCallback(
    async (id?: number) => {
      const ticket = ++sequence.current;
      setLoading(true);
      setError("");
      try {
        const runs = await getRiskRuns(caseId);
        const target = id ?? runs[0]?.id;
        const next = target ? await getRiskRun(target) : null;
        if (ticket !== sequence.current) return;
        setHistory(runs);
        setData(next);
        setSelected(next ? firstCheck(next) : null);
        setLoaded(true);
      } catch {
        if (ticket === sequence.current)
          setError(
            "Risk checks could not load. Select Refresh risk history to try again.",
          );
      } finally {
        if (ticket === sequence.current) setLoading(false);
      }
    },
    [caseId],
  );
  useEffect(() => {
    if (!active || loaded) return;
    const timer = setTimeout(() => void refresh(), 0);
    return () => clearTimeout(timer);
  }, [active, loaded, refresh]);
  async function run() {
    const ticket = ++sequence.current;
    requestId.current ??= crypto.randomUUID();
    setRunning(true);
    setError("");
    try {
      const next = await runRiskChecks(caseId, requestId.current);
      if (ticket !== sequence.current) return;
      setData(next);
      setSelected(firstCheck(next));
      setFilter("ALL");
      setHistory((runs) => [
        next.run,
        ...runs.filter((r) => r.id !== next.run.id),
      ]);
      requestId.current = null;
    } catch (e) {
      if (ticket === sequence.current)
        setError(
          e instanceof Error
            ? e.message
            : "Risk checks failed. Refresh history.",
        );
    } finally {
      if (ticket === sequence.current) setRunning(false);
    }
  }
  const busy = loading || running;
  const check = data?.checks.find((c) => c.id === selected);
  const executions =
    data?.executions.filter((e) => e.provider_check_pk === selected) || [];
  const summary = data?.run.summary_json;
  const checkCount = data?.checks.length ?? 0;
  const incomplete =
    data?.checks.filter(
      (c) => c.status === "PROVIDER_ERROR" || c.status === "INSUFFICIENT_DATA",
    ).length ?? 0;
  const notChecked =
    data?.checks.filter(
      (c) => c.status === "NOT_CHECKED" || c.status === "NOT_APPLICABLE",
    ).length ?? 0;
  return (
    <div className="risk-workspace" aria-busy={busy}>
      <div className="examination-heading">
        <SectionHeading title="Risk & Compliance">
          Synthetic screening providers and local trade controls. Results are
          signals for review; no final transaction decision.
        </SectionHeading>
        <div className="examination-actions">
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={() => void refresh()}
          >
            <RefreshCw size={14} />
            Refresh risk history
          </button>
          <button
            className="button button-primary"
            disabled={busy || !loaded}
            onClick={() => void run()}
          >
            <Play size={14} />
            {running
              ? "Checking…"
              : history.length
                ? "Rerun risk checks"
                : "Run risk checks"}
          </button>
        </div>
      </div>
      <p className="risk-provider-note">
        Demo Risk Data · Synthetic Screening Provider · Local duplicate search
      </p>
      {error && (
        <p className="examination-error" role="alert">
          {error}
        </p>
      )}
      {loading && (
        <p className="source-footnote" role="status">
          Loading stored risk runs…
        </p>
      )}
      {loaded && !data && (
        <EmptyState title="No risk run yet">
          Run risk checks to inspect available provider signals and local
          invoice candidates. Missing references stay visibly unchecked.
        </EmptyState>
      )}
      {data && (
        <>
          <div className="examination-runbar">
            <label>
              Risk run
              <select
                value={data.run.id}
                disabled={busy}
                onChange={(e) => void refresh(Number(e.target.value))}
              >
                {history.map((r) => (
                  <option key={r.id} value={r.id}>
                    Run {r.run_number} · {readable(r.status)} ·{" "}
                    {dateTime(r.started_at)}
                  </option>
                ))}
              </select>
            </label>
            <div>
              <RiskStatus value={data.run.status} />
              <p className="source-footnote">
                {data.run.ruleset_version} ·{" "}
                {dateTime(data.run.completed_at || data.run.started_at)}
              </p>
            </div>
          </div>
          {!data.inputs_current && (
            <p className="examination-notice" role="status">
              Current inputs, provider references or policies changed. This
              stored risk run remains unchanged; rerun to check current inputs.
            </p>
          )}
          {data.run.error_message && (
            <p className="examination-error" role="alert">
              {data.run.error_message}
            </p>
          )}
          <dl className="examination-counts">
            {[
              ["Provider checks", checkCount],
              ["Detected findings", summary?.findings ?? 0],
              ["Incomplete / errors", incomplete],
              ["Unchecked / inapplicable", notChecked],
            ].map(([label, count]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{count}</dd>
              </div>
            ))}
          </dl>
          <SectionHeading title="Check categories">
            Completed means execution finished. Clear applies only to the stated
            provider/search scope.
          </SectionHeading>
          <DataTable
            rows={categories.map((category, id) => ({
              id,
              category,
              checks: data.checks.filter((c) => c.provider_type === category),
            }))}
            empty=""
            columns={[
              { label: "Category", render: (r) => readable(r.category) },
              { label: "Checks", render: (r) => r.checks.length },
              {
                label: "Provider result",
                render: (r) => <RiskStatus value={aggregate(r.checks)} />,
              },
              {
                label: "Inspect",
                render: (r) => (
                  <a
                    className="examination-inspect"
                    href="#risk-provider-results"
                    onClick={() => setFilter(r.category)}
                  >
                    View checks
                    <span className="sr-only"> for {r.category}</span>
                  </a>
                ),
              },
            ]}
          />
          <div className="risk-section">
            <SectionHeading
              title="Detected risk findings"
              count={data.findings.length}
            >
              Calculated risk findings remain separate from documentary
              discrepancies and supplied reference risks.
            </SectionHeading>
            {data.findings.length ? (
              <DataTable
                rows={data.findings}
                empty=""
                columns={[
                  {
                    label: "Finding / severity",
                    render: (f) => (
                      <>
                        {f.title}
                        <span className="cell-subline">
                          {f.severity} · {readable(f.category)}
                        </span>
                      </>
                    ),
                  },
                  { label: "Subject", render: (f) => f.subject_value },
                  {
                    label: "Rule",
                    render: (f) => `${f.rule_id} v${f.rule_version}`,
                  },
                  {
                    label: "Evidence",
                    render: (f) => (
                      <a
                        className="examination-inspect"
                        href="#risk-evidence"
                        onClick={() => setSelected(f.provider_check_pk)}
                      >
                        View risk evidence
                        <span className="sr-only"> for {f.title}</span>
                      </a>
                    ),
                  },
                ]}
              />
            ) : (
              <p className="examination-empty">
                No risk findings were generated. Review unchecked and incomplete
                checks; this is not a clearance decision.
              </p>
            )}
          </div>
          {check && (
            <section
              id="risk-evidence"
              className="comparison-evidence"
              aria-label="Risk evidence"
            >
              <div className="comparison-heading">
                <h3>{check.input_json.subject || "No applicable subject"}</h3>
                <RiskStatus value={check.status} />
              </div>
              <p className="comparison-rule">
                {readable(check.provider_type)} · {check.provider_name} v
                {check.provider_version}
              </p>
              <p className="comparison-reason">{check.result_json.reason}</p>
              <div className="evidence-pair">
                <section
                  className="evidence-side"
                  aria-label="Originating source"
                >
                  <h3>Originating source</h3>
                  <p className="evidence-role">
                    {check.input_json.role ||
                      readable(check.input_json.subject_type)}
                    {check.input_json.country &&
                      ` · ${check.input_json.country}`}
                    {check.input_json.party_id &&
                      ` · Case party ${check.input_json.party_id}`}
                  </p>
                  {check.input_json.evidence.length ? (
                    check.input_json.evidence.map((e, index) => (
                      <details
                        className="risk-source"
                        key={e.fact_id}
                        open={index === 0}
                      >
                        <summary>
                          {readable(e.field_name)} · {e.filename} · page{" "}
                          {e.page_number}
                        </summary>
                        <dl className="evidence-values">
                          <div>
                            <dt>Raw value</dt>
                            <dd>{e.raw_value}</dd>
                          </div>
                          <div>
                            <dt>Normalized value</dt>
                            <dd>{evidenceValue(e.normalized_value)}</dd>
                          </div>
                          <div>
                            <dt>Confidence</dt>
                            <dd>
                              {e.confidence} ·{" "}
                              {e.source_verified
                                ? "Source verified"
                                : "Needs review"}
                            </dd>
                          </div>
                        </dl>
                        <blockquote>{e.source_text}</blockquote>
                        <Link
                          className="source-evidence-link"
                          href={sourceURL(e)}
                        >
                          Open original source
                          <ArrowUpRight size={14} />
                          <span className="sr-only"> {e.field_name}</span>
                        </Link>
                        <p className="source-footnote">
                          Version {e.version_number} · extraction run{" "}
                          {e.processing_run_number}
                        </p>
                      </details>
                    ))
                  ) : (
                    <p className="evidence-missing">
                      {check.input_json.party_id
                        ? "Identity comes from the stored operational case-party record; no document quotation is invented."
                        : "No eligible originating document fact for this check."}
                    </p>
                  )}
                </section>
                <section
                  className="evidence-side"
                  aria-label="Provider and policy"
                >
                  <h3>Provider and policy</h3>
                  <dl className="evidence-values">
                    <div>
                      <dt>Provider</dt>
                      <dd>
                        {check.provider_name} v{check.provider_version}
                      </dd>
                    </div>
                    <div>
                      <dt>Scope</dt>
                      <dd>
                        {check.result_json.synthetic
                          ? "Synthetic reference / local controls"
                          : "Provider result"}
                      </dd>
                    </div>
                    <div>
                      <dt>Result</dt>
                      <dd>{readable(check.status)}</dd>
                    </div>
                  </dl>
                  {check.result_json.matched_records.map((r) => (
                    <div className="risk-reference" key={r.reference_id}>
                      <h4>{r.name}</h4>
                      <p>
                        {r.reference_id} · {r.status}
                      </p>
                      <p>{r.note}</p>
                    </div>
                  ))}
                  {executions.map((e) => (
                    <div className="risk-reference" key={e.id}>
                      <h4>{e.rule_snapshot_json.name}</h4>
                      <p>
                        {e.rule_id} v{e.rule_version} ·{" "}
                        {e.rule_snapshot_json.severity}
                      </p>
                      <p>
                        {readable(e.status)} · {e.output_json.reason}
                      </p>
                    </div>
                  ))}
                  {Object.keys(check.result_json.details).length > 0 && (
                    <details className="risk-details">
                      <summary>Provider result details</summary>
                      <pre>
                        {JSON.stringify(check.result_json.details, null, 2)}
                      </pre>
                    </details>
                  )}
                  <p className="source-footnote">
                    Provider check {check.id} ·{" "}
                    {dateTime(check.completed_at || check.started_at)}
                  </p>
                </section>
              </div>
            </section>
          )}
          <div id="risk-provider-results" className="rule-results-heading">
            <SectionHeading title="Provider checks" count={checkCount} />
            <label>
              Risk category
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="ALL">All categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {readable(c)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <DataTable
            rows={data.checks.filter(
              (c) => filter === "ALL" || c.provider_type === filter,
            )}
            empty="No checks in this category."
            columns={[
              {
                label: "Subject / category",
                render: (c) => (
                  <>
                    {c.input_json.subject || "No applicable subject"}
                    <span className="cell-subline">
                      {readable(c.provider_type)}
                    </span>
                  </>
                ),
              },
              {
                label: "Provider / version",
                render: (c) => (
                  <>
                    {c.provider_name}
                    <span className="cell-subline">{c.provider_version}</span>
                  </>
                ),
              },
              {
                label: "Result",
                render: (c) => <RiskStatus value={c.status} />,
              },
              { label: "Reason", render: (c) => c.result_json.reason },
              {
                label: "Inspect",
                render: (c) => (
                  <a
                    className="examination-inspect"
                    href="#risk-evidence"
                    onClick={() => setSelected(c.id)}
                  >
                    Inspect check<span className="sr-only"> {c.id}</span>
                  </a>
                ),
              },
            ]}
          />
          <details className="examination-ledger">
            <summary>Risk rule executions · {data.executions.length}</summary>
            <DataTable
              rows={data.executions}
              empty="No risk rules executed."
              columns={[
                {
                  label: "Rule / version",
                  render: (e) => `${e.rule_id} v${e.rule_version}`,
                },
                { label: "Policy", render: (e) => e.rule_snapshot_json.name },
                {
                  label: "Result",
                  render: (e) => <RiskStatus value={e.status} />,
                },
                { label: "Reason", render: (e) => e.output_json.reason },
              ]}
            />
          </details>
        </>
      )}
    </div>
  );
}
