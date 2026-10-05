"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Play, RefreshCw } from "lucide-react";
import { DataTable, EmptyState, SectionHeading } from "@/components/ui";
import { readable } from "@/components/document-status";
import {
  getCaseEvidence,
  getExamination,
  getExaminations,
  runExamination,
} from "@/lib/api";
import { dateTime } from "@/lib/format";
import type {
  CurrentCaseEvidence,
  Evidence,
  ExaminationDetail,
  ExaminationRun,
  ResolvedSubject,
} from "@/types/examinations";

export function evidenceValue(value: unknown): string {
  if (value === null || value === undefined) return "Not available";
  if (typeof value === "object") {
    const v = value as Record<string, unknown>;
    if (v.amount !== undefined) return `${v.currency} ${v.amount}`;
    if (v.quantity !== undefined) return `${v.quantity} ${v.unit}`;
    return JSON.stringify(value);
  }
  return String(value);
}
function evidenceURL(e: Evidence) {
  const params = new URLSearchParams({
    version_id: String(e.document_version_id),
    run_id: String(e.processing_run_id),
  });
  if (e.fact_id !== null) params.set("fact_id", String(e.fact_id));
  return `/documents/${e.document_id}?${params}#source-page`;
}
function Result({ status }: { status: string }) {
  const tone =
    status === "MATCH" || status === "CLEAN"
      ? "matched"
      : status === "MISMATCH" ||
          status === "DISCREPANCIES_FOUND" ||
          status === "FAILED"
        ? "finding"
        : "review";
  return (
    <span className={`examination-result result-${tone}`}>
      {readable(status)}
    </span>
  );
}
function EvidenceSide({
  title,
  subject,
}: {
  title: string;
  subject: ResolvedSubject;
}) {
  const e = subject.evidence;
  return (
    <section className="evidence-side" aria-label={title}>
      <h3>{title}</h3>
      {!e ? (
        <p className="evidence-missing">
          {subject.reason}
          {subject.candidate_fact_ids.length > 0 &&
            ` · Candidate facts: ${subject.candidate_fact_ids.join(", ")}`}
        </p>
      ) : (
        <>
          <p className="evidence-role">
            {e.role} · {readable(e.field_name)}
          </p>
          <dl className="evidence-values">
            <div>
              <dt>Raw value</dt>
              <dd>{e.raw_value}</dd>
            </div>
            <div>
              <dt>Normalized value</dt>
              <dd>{evidenceValue(e.normalized_value)}</dd>
            </div>
            {e.derivation && (
              <div>
                <dt>Compared value</dt>
                <dd>
                  {evidenceValue(e.comparison_value)}
                  <span className="cell-subline">{e.derivation}</span>
                </dd>
              </div>
            )}
            <div>
              <dt>Confidence / support</dt>
              <dd>
                {e.confidence} · {readable(e.evidence_status)} ·{" "}
                {e.source_verified ? "Source verified" : "Needs source review"}
              </dd>
            </div>
          </dl>
          <blockquote>{e.source_text}</blockquote>
          <Link className="source-evidence-link" href={evidenceURL(e)}>
            {e.filename} · page {e.page_number}
            <ArrowUpRight size={14} />
          </Link>
          <p className="source-footnote">
            Source version {e.version_number} · extraction run{" "}
            {e.processing_run_number}
            {e.review_reason && ` · ${e.review_reason}`}
          </p>
        </>
      )}
    </section>
  );
}
function initialExecution(detail: ExaminationDetail) {
  return (
    (
      detail.executions.find((e) => e.status === "MISMATCH") ||
      detail.executions.find((e) => e.status !== "MATCH") ||
      detail.executions[0]
    )?.id ?? null
  );
}

export function ExaminationWorkspace({
  caseId,
  active,
  initialRunId,
}: {
  caseId: string;
  active: boolean;
  initialRunId?: number;
}) {
  const [history, setHistory] = useState<ExaminationRun[]>([]);
  const [detail, setDetail] = useState<ExaminationDetail | null>(null);
  const [current, setCurrent] = useState<CurrentCaseEvidence | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const requestId = useRef<string | null>(null);
  const refresh = useCallback(
    async (runId?: number) => {
      const ticket = ++sequence.current;
      setLoading(true);
      setError("");
      try {
        const [runs, facts] = await Promise.all([
          getExaminations(caseId),
          getCaseEvidence(caseId),
        ]);
        const id = runId ?? initialRunId ?? runs[0]?.id;
        if (id && !runs.some((r) => r.id === id))
          throw new Error("Unknown case examination run");
        const next = id ? await getExamination(id) : null;
        if (ticket !== sequence.current) return;
        setHistory(runs);
        setCurrent(facts);
        setDetail(next);
        setSelected(next ? initialExecution(next) : null);
        setLoaded(true);
      } catch {
        if (ticket === sequence.current)
          setError(
            "Examination could not load. Select Refresh history to try again.",
          );
      } finally {
        if (ticket === sequence.current) setLoading(false);
      }
    },
    [caseId, initialRunId],
  );
  useEffect(() => {
    if (!active || loaded) return;
    const timer = setTimeout(() => void refresh(), 0);
    return () => clearTimeout(timer);
  }, [active, loaded, refresh]);
  async function examine() {
    const ticket = ++sequence.current;
    requestId.current ??= crypto.randomUUID();
    setRunning(true);
    setError("");
    try {
      const next = await runExamination(caseId, requestId.current);
      if (ticket !== sequence.current) return;
      setDetail(next);
      setSelected(initialExecution(next));
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
            : "Examination could not run. Refresh history and try again.",
        );
    } finally {
      if (ticket === sequence.current) setRunning(false);
    }
  }
  const execution = detail?.executions.find((e) => e.id === selected);
  const executions =
    detail?.executions.filter((e) => filter === "ALL" || e.status === filter) ||
    [];
  const busy = loading || running;
  const summary = detail?.run.summary_json;
  function inspect(id: number) {
    setSelected(id);
  }
  return (
    <div className="examination-workspace" aria-busy={busy}>
      <div className="examination-heading">
        <SectionHeading title="Documentary examination">
          Cross-document comparisons from extracted source facts. This is not a
          final trade decision.
        </SectionHeading>
        <div className="examination-actions">
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={() => void refresh()}
          >
            <RefreshCw size={14} />
            Refresh history
          </button>
          <button
            className="button button-primary"
            disabled={busy || !loaded}
            onClick={() => void examine()}
          >
            <Play size={14} />
            {running
              ? "Examining…"
              : history.length
                ? "Rerun examination"
                : "Run examination"}
          </button>
        </div>
      </div>
      {error && (
        <p className="examination-error" role="alert">
          {error}
        </p>
      )}
      {loading && (
        <p role="status" className="source-footnote">
          Loading stored examinations and current facts…
        </p>
      )}
      {loaded && !detail && (
        <EmptyState title="No examination yet">
          Run an examination to compare the current document facts. Missing or
          uncertain evidence will be marked for review.
        </EmptyState>
      )}
      {detail && (
        <>
          <div className="examination-runbar">
            <label>
              Examination run
              <select
                value={detail.run.id}
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
              <Result status={detail.run.status} />
              <p className="source-footnote">
                {detail.run.ruleset_version} ·{" "}
                {dateTime(detail.run.completed_at || detail.run.started_at)}
              </p>
            </div>
          </div>
          {!detail.inputs_current && (
            <p className="examination-notice" role="status">
              Source facts, rules or confidence settings have changed. This
              stored run remains unchanged; rerun to examine current inputs.
            </p>
          )}
          {detail.run.error_message && (
            <p className="examination-error" role="alert">
              {detail.run.error_message} Refresh history or rerun examination.
            </p>
          )}
          <dl className="examination-counts">
            {(
              [
                ["Rules executed", summary?.rules_executed],
                ["Matched", summary?.matched],
                ["Discrepancies", summary?.findings],
                ["Incomplete", summary?.incomplete],
              ] as const
            ).map(([label, count]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{count ?? "—"}</dd>
              </div>
            ))}
          </dl>
          <SectionHeading
            title="Calculated findings"
            count={detail.findings.length}
          >
            Only supported mismatches create findings. Incomplete comparisons
            appear in the rule results below.
          </SectionHeading>
          {detail.findings.length ? (
            <DataTable
              rows={detail.findings}
              empty=""
              columns={[
                {
                  label: "Finding / severity",
                  render: (f) => (
                    <>
                      {f.title}
                      <span className="cell-subline">
                        {f.severity} · {f.rule_id} v{f.rule_version}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Expected",
                  render: (f) => (
                    <>
                      {evidenceValue(f.expected_json.comparison_value)}
                      <span className="cell-subline">
                        {f.expected_json.role}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Observed",
                  render: (f) => (
                    <>
                      {evidenceValue(f.observed_json.comparison_value)}
                      <span className="cell-subline">
                        {f.observed_json.role}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Evidence",
                  render: (f) => (
                    <a
                      className="examination-inspect"
                      href="#comparison-evidence"
                      onClick={() => inspect(f.rule_execution_pk)}
                    >
                      View evidence
                      <span className="sr-only"> for {f.title}</span>
                    </a>
                  ),
                },
              ]}
            />
          ) : (
            <p className="examination-empty">
              {detail.run.status === "CLEAN"
                ? "No documentary discrepancies were detected in this run."
                : "No supported discrepancies were detected. Review incomplete results before drawing a conclusion."}
            </p>
          )}
          {execution && (
            <section
              id="comparison-evidence"
              className="comparison-evidence"
              aria-label="Comparison evidence"
            >
              <div className="comparison-heading">
                <h3>{execution.rule_snapshot_json.name}</h3>
                <Result status={execution.status} />
              </div>
              <p className="comparison-rule">
                {execution.rule_id} v{execution.rule_version} ·{" "}
                {readable(execution.comparison_type)} ·{" "}
                {execution.rule_snapshot_json.severity}
              </p>
              <p className="comparison-reason">
                {execution.output_json.reason}
              </p>
              {Object.keys(execution.rule_snapshot_json.parameters).length >
                0 && (
                <p className="source-footnote">
                  Configured parameters:{" "}
                  {Object.entries(execution.rule_snapshot_json.parameters)
                    .map(([k, v]) => `${readable(k)}: ${evidenceValue(v)}`)
                    .join(" · ")}
                </p>
              )}
              <div className="evidence-pair">
                <EvidenceSide
                  title="Expected / governing source"
                  subject={execution.input_json.expected}
                />
                <EvidenceSide
                  title="Observed source"
                  subject={execution.input_json.observed}
                />
              </div>
            </section>
          )}
          <div className="rule-results-heading">
            <SectionHeading
              title="Rule results"
              count={detail.executions.length}
            />
            <label>
              Result filter
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                {[
                  "ALL",
                  ...new Set(detail.executions.map((e) => e.status)),
                ].map((s) => (
                  <option key={s} value={s}>
                    {s === "ALL" ? "All results" : readable(s)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {executions.length ? (
            <DataTable
              rows={executions}
              empty=""
              columns={[
                {
                  label: "Rule",
                  render: (e) => (
                    <>
                      {e.rule_snapshot_json.name}
                      <span className="cell-subline">
                        {e.rule_id} v{e.rule_version}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Comparison",
                  render: (e) => readable(e.comparison_type),
                },
                {
                  label: "Result",
                  render: (e) => <Result status={e.status} />,
                },
                {
                  label: "Inspect",
                  render: (e) => (
                    <a
                      className="examination-inspect"
                      href="#comparison-evidence"
                      onClick={() => inspect(e.id)}
                    >
                      Inspect<span className="sr-only"> {e.rule_id}</span>
                    </a>
                  ),
                },
              ]}
            />
          ) : (
            <p className="examination-empty">
              No rule results match this filter.
            </p>
          )}
          <details className="examination-ledger">
            <summary>Evidence relations · {detail.relations.length}</summary>
            <p className="source-footnote">
              Persisted links between the two source facts used in each
              comparison. Presence checks and missing facts create no relation.
            </p>
            {detail.relations.length ? (
              <DataTable
                rows={detail.relations}
                empty=""
                columns={[
                  {
                    label: "Governing fact",
                    render: (r) => (
                      <>
                        {r.expected?.role}
                        <span className="cell-subline">
                          {evidenceValue(r.expected?.comparison_value)}
                        </span>
                      </>
                    ),
                  },
                  {
                    label: "Relation",
                    render: (r) => readable(r.relation_type),
                  },
                  {
                    label: "Observed fact",
                    render: (r) => (
                      <>
                        {r.observed?.role}
                        <span className="cell-subline">
                          {evidenceValue(r.observed?.comparison_value)}
                        </span>
                      </>
                    ),
                  },
                  {
                    label: "Result",
                    render: (r) => <Result status={r.status} />,
                  },
                  {
                    label: "Inspect",
                    render: (r) => (
                      <a
                        className="examination-inspect"
                        href="#comparison-evidence"
                        onClick={() => inspect(r.rule_execution_pk)}
                      >
                        Inspect relation<span className="sr-only"> {r.id}</span>
                      </a>
                    ),
                  },
                ]}
              />
            ) : (
              <p className="examination-empty">
                This run has no two-fact relations.
              </p>
            )}
          </details>
        </>
      )}
      {current && (
        <details className="examination-ledger">
          <summary>Current extracted facts · {current.facts.length}</summary>
          <p className="source-footnote">
            Latest source versions and extraction runs only. Examination
            confidence threshold: {current.confidence_threshold}. Stored runs
            retain their own source snapshots.
          </p>
          {current.facts.length ? (
            <DataTable
              rows={current.facts.map((f) => ({ ...f, id: f.fact_id! }))}
              empty=""
              columns={[
                {
                  label: "Field / source",
                  render: (f) => (
                    <>
                      {readable(f.field_name)}
                      <span className="cell-subline">
                        {f.filename} · page {f.page_number}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Normalized value",
                  render: (f) => evidenceValue(f.normalized_value),
                },
                {
                  label: "Confidence / evidence",
                  render: (f) => (
                    <>
                      {f.confidence}
                      <span className="cell-subline">
                        {readable(f.evidence_status)} ·{" "}
                        {f.source_verified ? "Source verified" : "Needs review"}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Original",
                  render: (f) => (
                    <Link className="examination-inspect" href={evidenceURL(f)}>
                      View source
                      <span className="sr-only"> {f.field_name}</span>
                    </Link>
                  ),
                },
              ]}
            />
          ) : (
            <p className="examination-empty">
              No current extracted facts. Process the original PDFs in Documents
              first.
            </p>
          )}
        </details>
      )}
    </div>
  );
}
