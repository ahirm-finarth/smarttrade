"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { DataTable, EmptyState, SectionHeading } from "@/components/ui";
import { readable } from "@/components/document-status";
import {
  DecisionHistory,
  DecisionOverview,
  DecisionState,
  useDecisionData,
} from "@/components/decision-workspace";
import { getDemoActors, governedCommand } from "@/lib/api";
import { dateTime } from "@/lib/format";
import type {
  DecisionDetail,
  DemoActor,
  WorkflowTask,
} from "@/types/decisions";

function TaskForm({
  task,
  data,
  actorId,
  busy,
  submit,
}: {
  task: WorkflowTask;
  data: DecisionDetail;
  actorId: string;
  busy: boolean;
  submit: (path: string, payload: Record<string, unknown>) => Promise<void>;
}) {
  const [chosen, setChosen] = useState("");
  const [comment, setComment] = useState("");
  const [queue, setQueue] = useState("SUPERVISOR_ESCALATION");
  const action = task.available_actions.includes(chosen)
    ? chosen
    : task.available_actions.find((a) => a !== "START") ||
      task.available_actions[0] ||
      "";
  async function send(event: FormEvent) {
    event.preventDefault();
    await submit(`/tasks/${task.id}/actions`, {
      actor_id: actorId,
      action,
      comment,
      expected_revision: data.workflow!.revision,
      ...(action === "ESCALATE" ? { target_queue: queue } : {}),
    });
  }
  return (
    <section
      className="workflow-task"
      id={`workflow-task-${task.id}`}
      aria-label={`Task ${task.id}`}
    >
      <div className="comparison-heading">
        <div>
          <h3>{task.title}</h3>
          <p>
            Task #{task.id} · {readable(task.assigned_role)} · {task.priority}
          </p>
        </div>
        <DecisionState value={task.status} />
      </div>
      <p>{task.description}</p>
      <p className="source-footnote">
        {task.assigned_actor_id
          ? `Claimed by ${task.assigned_actor_id}`
          : "Unclaimed"}{" "}
        · Reasons: {task.reason_ids_json.join(", ") || "Approval control"}
      </p>
      {task.available_actions.length ? (
        <form className="workflow-form" onSubmit={send}>
          <label>
            Action for task {task.id}
            <select
              value={action}
              disabled={busy}
              onChange={(e) => setChosen(e.target.value)}
            >
              {task.available_actions.map((a) => (
                <option key={a} value={a}>
                  {readable(a)}
                </option>
              ))}
            </select>
          </label>
          {action === "ESCALATE" && (
            <label>
              Escalation queue
              <select
                value={queue}
                disabled={busy}
                onChange={(e) => setQueue(e.target.value)}
              >
                {[
                  "TRADE_REVIEW",
                  "COMPLIANCE_REVIEW",
                  "LEGAL_REVIEW",
                  "SUPERVISOR_ESCALATION",
                ].map((q) => (
                  <option key={q} value={q}>
                    {readable(q)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Rationale for task {task.id}
            <textarea
              value={comment}
              maxLength={4000}
              minLength={action === "START" ? 0 : 3}
              required={action !== "START"}
              disabled={busy}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Record the review and evidence supporting this action."
            />
          </label>
          <button
            className="button button-primary"
            disabled={busy || (action !== "START" && comment.trim().length < 3)}
          >
            {busy ? "Saving action…" : "Record task action"}
          </button>
        </form>
      ) : (
        <p className="source-footnote">
          {data.inputs_current &&
          !data.workflow?.final_outcome &&
          ["OPEN", "IN_PROGRESS"].includes(task.status)
            ? "Choose an authorized demo actor. Claimed tasks and maker/checker segregation are enforced by the server."
            : "Read-only task history."}
        </p>
      )}
    </section>
  );
}

function OverrideForm({
  data,
  actorId,
  busy,
  submit,
}: {
  data: DecisionDetail;
  actorId: string;
  busy: boolean;
  submit: (path: string, payload: Record<string, unknown>) => Promise<void>;
}) {
  const latest = new Map(
    data.resolutions.map((r) => [r.decision_reason_pk, r.resolution]),
  );
  const eligible = data.reasons.filter(
    (r) =>
      data.unresolved_reason_ids.includes(r.id) &&
      ["DOCUMENTARY_FINDING", "RISK_REVIEW"].includes(r.reason_code) &&
      latest.get(r.id) === "CONFIRM_ISSUE",
  );
  const [selected, setSelected] = useState<number[]>([]);
  const [rationale, setRationale] = useState("");
  const [reference, setReference] = useState("");
  const ids = selected.filter((id) => eligible.some((r) => r.id === id));
  if (
    !data.demo_actor.roles.includes("SUPERVISOR") ||
    !data.inputs_current ||
    data.workflow?.final_outcome ||
    data.run.recommended_decision !== "REFER"
  )
    return null;
  async function send(event: FormEvent) {
    event.preventDefault();
    await submit(`/decisions/${data.run.id}/override`, {
      actor_id: actorId,
      reason_code: "ACCEPT_REVIEWED_EXCEPTION",
      rationale,
      reason_ids: ids,
      evidence_reference: reference || null,
      expected_revision: data.workflow!.revision,
    });
  }
  return (
    <section
      className="workflow-task"
      aria-label="Supervisor exception acceptance"
    >
      <h3>Accept reviewed REFER exceptions</h3>
      <p>
        Acceptance records an exception for the selected reasons. The system
        recommendation stays REFER; a distinct maker and checker must still
        approve. Hard BLOCK and missing mandatory evidence cannot be waived.
      </p>
      {eligible.length ? (
        <form className="workflow-form" onSubmit={send}>
          <fieldset>
            <legend>Specialist-confirmed issues</legend>
            {eligible.map((r) => (
              <label className="workflow-check" key={r.id}>
                <input
                  type="checkbox"
                  disabled={busy}
                  checked={ids.includes(r.id)}
                  onChange={(e) =>
                    setSelected((prev) =>
                      e.target.checked
                        ? [...prev, r.id]
                        : prev.filter((id) => id !== r.id),
                    )
                  }
                />
                <span>
                  Reason #{r.id} · {r.title}
                </span>
              </label>
            ))}
          </fieldset>
          <label>
            Exception acceptance rationale
            <textarea
              required
              minLength={8}
              maxLength={4000}
              disabled={busy}
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
            />
          </label>
          <label>
            Evidence reference (optional)
            <input
              maxLength={255}
              disabled={busy}
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          </label>
          <button
            className="button button-primary"
            disabled={busy || !ids.length || rationale.trim().length < 8}
          >
            Record exception acceptance
          </button>
        </form>
      ) : (
        <p className="source-footnote">
          No eligible issues yet. Specialists must confirm each issue before
          supervisory acceptance.
        </p>
      )}
    </section>
  );
}

export function GovernedApprovals({
  caseId,
  active,
  initialId,
}: {
  caseId: string;
  active: boolean;
  initialId?: number;
}) {
  const [actorId, setActorId] = useState("maker.demo");
  const [actors, setActors] = useState<DemoActor[]>([]);
  const [saving, setSaving] = useState(false);
  const pending = useRef<{ key: string; id: string } | null>(null);
  const store = useDecisionData(caseId, active, actorId, initialId);
  const { data, history, error, setError } = store;
  const busy =
    store.busy ||
    saving ||
    Boolean(data && data.demo_actor.actor_id !== actorId);
  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    getDemoActors()
      .then((rows) => {
        if (!cancelled) setActors(rows);
      })
      .catch(() => {
        if (!cancelled)
          setError("Demo actors could not load. Refresh this page to retry.");
      });
    return () => {
      cancelled = true;
    };
  }, [active, setError]);
  async function submit(path: string, payload: Record<string, unknown>) {
    const key = JSON.stringify({ path, payload });
    if (pending.current?.key !== key)
      pending.current = { key, id: crypto.randomUUID() };
    setSaving(true);
    setError("");
    try {
      const next = await governedCommand<DecisionDetail>(path, {
        ...payload,
        request_id: pending.current.id,
      });
      store.setData(next);
      pending.current = null;
      // Commands return the acting identity's available actions; retain exact decision version.
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Action could not be saved. Refresh workflow before retrying.",
      );
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="decision-workspace" aria-busy={busy}>
      <div className="examination-heading">
        <SectionHeading title="Governed Approvals & Workflow">
          Specialist reviews, explicit maker/checker actions and appended audit
          history.
        </SectionHeading>
        <button
          className="button button-secondary"
          disabled={busy}
          onClick={() => void store.refresh()}
        >
          <RefreshCw size={15} />
          Refresh workflow
        </button>
      </div>
      <div className="workflow-identity">
        <label>
          Demo actor
          <select
            disabled={busy || !actors.length}
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
          >
            {actors.map((a) => (
              <option value={a.actor_id} key={a.actor_id}>
                {a.display_name} · {a.actor_id}
              </option>
            ))}
          </select>
        </label>
        <p>
          Demo identity selector; no production authentication. Roles and
          segregation of duties are enforced by the backend.
        </p>
      </div>
      {error && (
        <p className="examination-warning" role="alert">
          {error}
        </p>
      )}
      <DecisionHistory
        history={history}
        data={data}
        busy={busy}
        onSelect={(id) => void store.refresh(id)}
      />
      {!store.loaded && !error && (
        <p role="status">Loading governed workflow…</p>
      )}
      {store.loaded && !data && (
        <EmptyState title="No governed workflow">
          Generate a decision in the Decision tab to create the appropriate
          tasks.
        </EmptyState>
      )}
      {data && (
        <>
          <DecisionOverview data={data} caseId={caseId} />
          {data.maker_actor_ids.includes(actorId) &&
            data.demo_actor.roles.includes("TRADE_CHECKER") && (
              <p className="examination-warning" role="status">
                Segregation of duties: this actor submitted as maker and cannot
                check the same decision. Select a different checker.
              </p>
            )}
          <SectionHeading title="Workflow tasks" count={data.tasks.length} />
          <p className="source-footnote">
            Workflow revision {data.workflow?.revision} ·{" "}
            <Link
              href={`/cases/${caseId}?tab=decision&decision_id=${data.run.id}`}
            >
              Open decision reasons and source evidence
            </Link>
          </p>
          {data.tasks.map((task) => (
            <TaskForm
              key={`${data.run.id}:${actorId}:${task.id}`}
              task={task}
              data={data}
              actorId={actorId}
              busy={busy}
              submit={submit}
            />
          ))}
          <OverrideForm
            key={`${data.run.id}:${actorId}`}
            data={data}
            actorId={actorId}
            busy={busy}
            submit={submit}
          />
          <section className="risk-section">
            <SectionHeading
              title="Recorded finding resolutions"
              count={data.resolutions.length}
            />
            <DataTable
              rows={data.resolutions}
              empty="No human finding resolutions recorded. Source findings remain unchanged."
              columns={[
                {
                  label: "Reason / task",
                  render: (r) => `#${r.decision_reason_pk} / #${r.task_pk}`,
                },
                { label: "Resolution", render: (r) => readable(r.resolution) },
                {
                  label: "Actor / role",
                  render: (r) => (
                    <>
                      {r.actor_id}
                      <span className="cell-subline">
                        {readable(r.actor_role)}
                      </span>
                    </>
                  ),
                },
                { label: "Rationale", render: (r) => r.rationale },
                { label: "Recorded", render: (r) => dateTime(r.created_at) },
              ]}
            />
          </section>
          <section className="risk-section">
            <SectionHeading
              title="Exception acceptance history"
              count={data.overrides.length}
            />
            <DataTable
              rows={data.overrides}
              empty="No overrides recorded. Hard blocks and missing mandatory evidence cannot be waived."
              columns={[
                {
                  label: "Actor / role",
                  render: (r) => (
                    <>
                      {r.actor_id}
                      <span className="cell-subline">
                        {readable(r.actor_role)}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Acceptance",
                  render: (r) => (
                    <>
                      {r.from_decision} → {r.to_decision}
                      <span className="cell-subline">
                        Eligibility only; maker/checker still required
                      </span>
                    </>
                  ),
                },
                {
                  label: "Reasons / rationale",
                  render: (r) => (
                    <>
                      #{r.reason_ids_json.join(", #")}
                      <span className="cell-subline">{r.rationale}</span>
                    </>
                  ),
                },
                {
                  label: "Evidence reference",
                  render: (r) => r.evidence_reference || "Not supplied",
                },
                { label: "Recorded", render: (r) => dateTime(r.created_at) },
              ]}
            />
          </section>
          <section className="risk-section">
            <SectionHeading
              title="Workflow event history"
              count={data.events.length}
            />
            <DataTable
              rows={data.events}
              empty="No workflow events recorded."
              columns={[
                { label: "Recorded", render: (r) => dateTime(r.created_at) },
                {
                  label: "Event / task",
                  render: (r) => (
                    <>
                      {readable(r.event_type)}
                      <span className="cell-subline">
                        {r.task_pk
                          ? `Task #${r.task_pk}`
                          : `Decision #${data.run.id}`}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Actor / role",
                  render: (r) => (
                    <>
                      {r.actor_id}
                      <span className="cell-subline">
                        {readable(r.actor_role)}
                      </span>
                    </>
                  ),
                },
                {
                  label: "Comment",
                  render: (r) => r.comment || "System event",
                },
              ]}
            />
          </section>
        </>
      )}
    </div>
  );
}
