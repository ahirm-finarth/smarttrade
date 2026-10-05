"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Play, RefreshCw } from "lucide-react";
import {
  DataTable,
  EmptyState,
  Outcome,
  SectionHeading,
} from "@/components/ui";
import { readable } from "@/components/document-status";
import { evidenceValue } from "@/components/examination-workspace";
import { getDecision, getDecisions, governedCommand } from "@/lib/api";
import { dateTime } from "@/lib/format";
import {
  sourceEvidence,
  type AdvisoryResponse,
  type DecisionDetail,
  type DecisionReason,
  type DecisionRun,
  type ExceptionAdvice,
} from "@/types/decisions";

export function DecisionState({ value }: { value: string }) {
  const kind = ["PASS", "APPROVED", "COMPLETED", "CONFIRM_CLEAR"].includes(
    value,
  )
    ? "result-matched"
    : ["BLOCK", "REJECT", "REJECTED", "FAILED"].includes(value)
      ? "result-finding"
      : [
            "REFER",
            "REFERRED",
            "NEEDS_INFORMATION",
            "AWAITING_SPECIALIST",
          ].includes(value)
        ? "result-review"
        : "outcome-neutral";
  return (
    <span className={`examination-result ${kind}`}>{readable(value)}</span>
  );
}

export function useDecisionData(
  caseId: string,
  active: boolean,
  actorId = "maker.demo",
  initialId?: number,
) {
  const [history, setHistory] = useState<DecisionRun[]>([]);
  const [data, setData] = useState<DecisionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const selectedRun = useRef<number | undefined>(initialId);
  const generationId = useRef<string | null>(null);
  const refresh = useCallback(
    async (id?: number) => {
      const ticket = ++sequence.current;
      setLoading(true);
      setError("");
      try {
        const runs = await getDecisions(caseId);
        const target = id ?? initialId ?? runs[0]?.id;
        if (target && !runs.some((r) => r.id === target))
          throw new Error("This decision does not belong to this case.");
        const next = target ? await getDecision(target, actorId) : null;
        if (ticket !== sequence.current) return;
        selectedRun.current = next?.run.id;
        setData(next);
        setHistory(runs);
        setLoaded(true);
      } catch (e) {
        if (ticket === sequence.current)
          setError(
            e instanceof Error
              ? e.message
              : "Decision history could not load. Refresh to retry.",
          );
      } finally {
        if (ticket === sequence.current) setLoading(false);
      }
    },
    [caseId, actorId, initialId],
  );
  useEffect(() => {
    if (!active) return;
    const timer = setTimeout(() => void refresh(selectedRun.current), 0);
    return () => clearTimeout(timer);
  }, [active, refresh]);
  async function generate() {
    const ticket = ++sequence.current;
    generationId.current ??= crypto.randomUUID();
    setRunning(true);
    setError("");
    try {
      const next = await governedCommand<DecisionDetail>(
        `/cases/${encodeURIComponent(caseId)}/decisions`,
        { request_id: generationId.current },
      );
      if (ticket !== sequence.current) return;
      selectedRun.current = next.run.id;
      setData(next);
      setLoaded(true);
      setHistory((runs) => [
        next.run,
        ...runs.filter((r) => r.id !== next.run.id),
      ]);
      generationId.current = null;
    } catch (e) {
      if (ticket === sequence.current)
        setError(
          e instanceof Error
            ? e.message
            : "Decision generation failed. Refresh history.",
        );
    } finally {
      if (ticket === sequence.current) setRunning(false);
    }
  }
  return {
    data,
    setData,
    history,
    loaded,
    loading,
    running,
    error,
    setError,
    refresh,
    generate,
    busy: loading || running,
  };
}

export function DecisionHistory({
  history,
  data,
  busy,
  onSelect,
}: {
  history: DecisionRun[];
  data: DecisionDetail | null;
  busy: boolean;
  onSelect: (id: number) => void;
}) {
  return (
    <div className="examination-runbar">
      <label>
        Decision version
        <select
          disabled={busy || !history.length}
          value={data?.run.id || ""}
          onChange={(e) => onSelect(Number(e.target.value))}
        >
          {!history.length && <option value="">No saved decision</option>}
          {history.map((r) => (
            <option value={r.id} key={r.id}>
              Version {r.run_number} ·{" "}
              {r.recommended_decision || readable(r.status)} ·{" "}
              {dateTime(r.created_at)}
            </option>
          ))}
        </select>
      </label>
      {data && (
        <div>
          <DecisionState value={data.run.status} />
          <p>
            {data.run.ruleset_version} · {dateTime(data.run.created_at)}
          </p>
        </div>
      )}
    </div>
  );
}

export function DecisionOverview({
  data,
  caseId,
}: {
  data: DecisionDetail;
  caseId: string;
}) {
  const doc = data.input_snapshot.documentary;
  const risk = data.input_snapshot.risk;
  return (
    <>
      {!data.inputs_current && (
        <p className="examination-warning" role="status">
          Decision is stale. New decision required before approval. Refresh
          source runs and regenerate.
        </p>
      )}
      <dl className="decision-outcomes">
        <div>
          <dt>System recommendation</dt>
          <dd>
            <Outcome value={data.run.recommended_decision} />
          </dd>
          <p>Deterministic policy · {data.run.ruleset_version}</p>
        </div>
        <div>
          <dt>Governed outcome</dt>
          <dd>
            {data.effective_final_outcome ? (
              <Outcome value={data.effective_final_outcome} />
            ) : (
              <strong>
                {data.inputs_current
                  ? "Pending human approval"
                  : "New decision required"}
              </strong>
            )}
          </dd>
          <p>
            {data.inputs_current
              ? readable(data.workflow?.state || "PENDING")
              : data.workflow?.final_outcome
                ? `Historical outcome: ${data.workflow.final_outcome}; inactive for current evidence`
                : "Historical workflow; actions unavailable"}
          </p>
        </div>
      </dl>
      <p className="source-footnote">
        A recommendation does not approve a case. A governed PASS requires maker
        and checker; no payment or posting occurs.
      </p>
      <dl className="decision-sources">
        <div>
          <dt>Documentary source</dt>
          <dd>
            {doc ? (
              <Link
                href={`/cases/${caseId}?tab=examination&examination_run_id=${doc.id}`}
              >
                Examination #{doc.id} · version {doc.run_number} ·{" "}
                {readable(doc.status)} <ArrowUpRight size={13} />
              </Link>
            ) : (
              "No source run"
            )}
          </dd>
        </div>
        <div>
          <dt>Risk source</dt>
          <dd>
            {risk ? (
              <Link
                href={`/cases/${caseId}?tab=risk_compliance&risk_run_id=${risk.id}`}
              >
                Risk run #{risk.id} · version {risk.run_number} ·{" "}
                {readable(risk.status)} <ArrowUpRight size={13} />
              </Link>
            ) : (
              "No source run"
            )}
          </dd>
        </div>
      </dl>
    </>
  );
}

function ReasonEvidence({ reason }: { reason: DecisionReason }) {
  const evidence = sourceEvidence(reason);
  return (
    <section
      id="decision-reason-evidence"
      className="comparison-inspector"
      aria-label="Decision reason evidence"
    >
      <div className="comparison-heading">
        <div>
          <h3>{reason.title}</h3>
          <p>
            Reason #{reason.id} · {readable(reason.reason_code)} ·{" "}
            {reason.severity}
          </p>
        </div>
        <DecisionState value={reason.impact} />
      </div>
      <dl className="decision-sources">
        <div>
          <dt>Source status</dt>
          <dd>{readable(reason.source_status)}</dd>
        </div>
        <div>
          <dt>Deterministic queue</dt>
          <dd>
            {reason.route_to ? readable(reason.route_to) : "No referral task"}
          </dd>
        </div>
      </dl>
      {evidence.length ? (
        <div className="evidence-pair">
          {evidence.map((e) => (
            <section
              className="evidence-side"
              aria-label={`${e.role} source`}
              key={`${e.document_version_id}:${e.fact_id}`}
            >
              <h3>{e.role}</h3>
              <p className="evidence-role">
                {readable(e.field_name)} · {e.filename} · page {e.page_number}
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
                <div>
                  <dt>Confidence / support</dt>
                  <dd>
                    {e.confidence} ·{" "}
                    {e.source_verified
                      ? "Source verified"
                      : "Needs source review"}
                  </dd>
                </div>
              </dl>
              <blockquote>{e.source_text}</blockquote>
              <Link
                className="source-evidence-link"
                href={`/documents/${e.document_id}?version_id=${e.document_version_id}&run_id=${e.processing_run_id}&fact_id=${e.fact_id}#source-page`}
              >
                Open original source <ArrowUpRight size={13} />
              </Link>
              <p className="source-footnote">
                Source version {e.version_number} · extraction run{" "}
                {e.processing_run_number}
              </p>
            </section>
          ))}
        </div>
      ) : (
        <p className="evidence-missing">
          This reason refers to the stored control or policy audit below. No
          source quotation is invented.
        </p>
      )}
      <details className="risk-details">
        <summary>Stored reason and control evidence</summary>
        <pre>{JSON.stringify(reason.evidence_json, null, 2)}</pre>
      </details>
    </section>
  );
}

export function DecisionWorkspace({
  caseId,
  active,
  initialId,
}: {
  caseId: string;
  active: boolean;
  initialId?: number;
}) {
  const store = useDecisionData(caseId, active, "maker.demo", initialId);
  const { data, history, busy, error } = store;
  const [selected, setSelected] = useState<number | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [drafting, setDrafting] = useState(false);
  const [advice, setAdvice] = useState<{
    decisionId: number;
    output: ExceptionAdvice;
  } | null>(null);
  const adviceId = useRef<string | null>(null);
  const adviceDecision = useRef<number | null>(null);
  const reason =
    data?.reasons.find((r) => r.id === selected) ||
    data?.reasons.find((r) => r.impact !== "INFO") ||
    data?.reasons[0];
  const savedAdvice = data?.events
    .filter((e) => e.event_type === "EXCEPTION_SUMMARY_GENERATED")
    .at(-1)?.metadata_json.output as ExceptionAdvice | undefined;
  const currentAdvice =
    advice?.decisionId === data?.run.id ? advice?.output : savedAdvice;
  async function draft() {
    if (!data) return;
    if (adviceDecision.current !== data.run.id) {
      adviceId.current = null;
      adviceDecision.current = data.run.id;
    }
    adviceId.current ??= crypto.randomUUID();
    setDrafting(true);
    store.setError("");
    try {
      const next = await governedCommand<AdvisoryResponse>(
        `/decisions/${data.run.id}/exception-summary`,
        { actor_id: "maker.demo", request_id: adviceId.current },
        true,
      );
      setAdvice({ decisionId: next.decision_id, output: next.output });
      adviceId.current = null;
    } catch (e) {
      store.setError(
        e instanceof Error ? e.message : "Advisory draft unavailable.",
      );
    } finally {
      setDrafting(false);
    }
  }
  return (
    <div className="decision-workspace" aria-busy={busy || drafting}>
      <div className="examination-heading">
        <SectionHeading title="Smart Trade Decision">
          Versioned system recommendation and a separate governed human outcome.
        </SectionHeading>
        <div className="examination-actions">
          <button
            className="button button-secondary"
            disabled={busy || drafting}
            onClick={() => void store.refresh()}
          >
            <RefreshCw size={15} /> Refresh decision history
          </button>
          <button
            className="button button-primary"
            disabled={busy || drafting}
            onClick={() => void store.generate()}
          >
            <Play size={15} />{" "}
            {store.running
              ? "Generating decision…"
              : data
                ? "Regenerate decision"
                : "Run decision"}
          </button>
        </div>
      </div>
      <p className="risk-provider-note">
        Synthetic demo policy · source-backed reasons · maker/checker required
      </p>
      {error && (
        <p className="examination-warning" role="alert">
          {error}
        </p>
      )}
      <DecisionHistory
        history={history}
        data={data}
        busy={busy || drafting}
        onSelect={(id) => void store.refresh(id)}
      />
      {!store.loaded && !error && (
        <p className="source-footnote" role="status">
          Loading saved decisions…
        </p>
      )}
      {store.loaded && !data && (
        <EmptyState title="No decision generated">
          Run decision after examining the source documents and risk controls.
          No final outcome exists yet.
        </EmptyState>
      )}
      {data && (
        <>
          <DecisionOverview data={data} caseId={caseId} />
          <dl className="examination-counts">
            {[
              [
                "Documentary findings",
                data.run.summary_json.documentary_findings,
              ],
              ["Risk findings", data.run.summary_json.risk_findings],
              ["Unresolved reasons", data.unresolved_reason_ids.length],
              [
                "Optional unchecked controls",
                data.run.summary_json.optional_unchecked,
              ],
            ].map(([label, count]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{count}</dd>
              </div>
            ))}
          </dl>
          <details className="decision-policy">
            <summary>Decision and approval policy</summary>
            <dl className="metadata-list">
              <div>
                <dt>Mandatory demo controls</dt>
                <dd>
                  {data.input_snapshot.policy.mandatory_categories
                    .map(readable)
                    .join(", ")}
                </dd>
              </div>
              <div>
                <dt>Optional reference controls</dt>
                <dd>
                  {data.input_snapshot.policy.optional_categories
                    .map(readable)
                    .join(", ")}
                  ; independent financing-event control
                </dd>
              </div>
              <div>
                <dt>Approval requirements</dt>
                <dd>
                  Distinct maker and checker. Review-level risk may be cleared
                  by specialists; documentary issues require reviewed
                  supervisory acceptance.
                </dd>
              </div>
              <div>
                <dt>Unwaivable controls</dt>
                <dd>
                  Hard BLOCK, stale inputs and incomplete/missing mandatory
                  evidence.
                </dd>
              </div>
              <div>
                <dt>Routing version</dt>
                <dd>{data.input_snapshot.routing_policy.version}</dd>
              </div>
            </dl>
            <p className="source-footnote">
              Optional means outside this limited demo policy&apos;s approval
              prerequisites. Missing references remain unchecked.
            </p>
          </details>
          <div className="rule-results-heading">
            <SectionHeading
              title="Decision reasons"
              count={data.reasons.length}
            />
            <label>
              Reason impact
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="ALL">All reasons</option>
                <option value="REFER">Referral reasons</option>
                <option value="BLOCK">Hard controls</option>
                <option value="INFO">Policy / optional controls</option>
              </select>
            </label>
          </div>
          <DataTable
            rows={data.reasons.filter(
              (r) => filter === "ALL" || r.impact === filter,
            )}
            empty="No reasons in this category."
            columns={[
              {
                label: "Reason / source",
                render: (r) => (
                  <>
                    {r.title}
                    <span className="cell-subline">
                      #{r.id} · {readable(r.reason_type)}
                    </span>
                  </>
                ),
              },
              {
                label: "Impact / status",
                render: (r) => (
                  <>
                    <DecisionState value={r.impact} />
                    <span className="cell-subline">
                      {readable(r.source_status)}
                    </span>
                  </>
                ),
              },
              {
                label: "Queue",
                render: (r) =>
                  r.route_to ? readable(r.route_to) : "No referral",
              },
              {
                label: "Resolution",
                render: (r) =>
                  r.impact === "INFO"
                    ? "Disclosed"
                    : data.unresolved_reason_ids.includes(r.id)
                      ? "Unresolved"
                      : "Recorded human resolution",
              },
              {
                label: "Evidence",
                render: (r) => (
                  <a
                    className="examination-inspect"
                    href="#decision-reason-evidence"
                    onClick={() => setSelected(r.id)}
                    aria-label={`Inspect decision reason ${r.id}`}
                  >
                    Inspect reason
                  </a>
                ),
              },
            ]}
          />
          {reason && <ReasonEvidence reason={reason} />}
          <details className="decision-advisory">
            <summary>Optional Exception Resolution Agent</summary>
            <p>
              Advisory writing only. Existing reasons and deterministic routing
              remain authoritative. Drafts cannot resolve or approve a case.
            </p>
            <button
              className="button button-secondary"
              disabled={busy || drafting || !data.inputs_current}
              onClick={() => void draft()}
            >
              {drafting
                ? "Drafting advisory summary…"
                : "Draft exception summary"}
            </button>
            {currentAdvice && (
              <div
                className="advisory-output"
                aria-label="Advisory exception draft"
              >
                <h3>Advisory summary</h3>
                <p>{currentAdvice.executive_summary}</p>
                <p>
                  Suggested queue (advisory):{" "}
                  {readable(currentAdvice.suggested_queue)}
                </p>
                {currentAdvice.grouped_issues.map((g, i) => (
                  <p key={i}>
                    {g.label} · Source reasons: {g.reason_ids.join(", ")}
                  </p>
                ))}
                <h3>Draft reviewer note</h3>
                <p>{currentAdvice.draft_reviewer_note}</p>
                <h3>Draft information request</h3>
                <p>
                  {currentAdvice.draft_information_request ||
                    "No draft request supplied."}
                </p>
              </div>
            )}
          </details>
        </>
      )}
    </div>
  );
}
