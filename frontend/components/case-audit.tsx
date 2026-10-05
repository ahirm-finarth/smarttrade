"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { EmptyState, SectionHeading } from "@/components/ui";
import { readable } from "@/components/document-status";
import { getAudit } from "@/lib/api";
import { dateTime } from "@/lib/format";
import type { AuditEntry } from "@/types/decisions";

export function CaseAudit({
  caseId,
  active,
}: {
  caseId: string;
  active: boolean;
}) {
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("ALL");
  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRows(await getAudit(caseId));
      setLoaded(true);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Audit history could not load. Refresh to retry.",
      );
    } finally {
      setLoading(false);
    }
  }, [caseId]);
  useEffect(() => {
    if (!active) return;
    const timer = setTimeout(() => void refresh(), 0);
    return () => clearTimeout(timer);
  }, [active, refresh]);
  const visible = rows.filter(
    (r) => filter === "ALL" || r.event_type === filter,
  );
  return (
    <div className="decision-workspace" aria-busy={loading}>
      <div className="examination-heading">
        <SectionHeading title="Case Audit" count={rows.length}>
          Read-only history of document processing, examinations, risk runs,
          decisions and governed actions. Newest events first; timestamps in
          IST.
        </SectionHeading>
        <button
          className="button button-secondary"
          disabled={loading}
          onClick={() => void refresh()}
        >
          <RefreshCw size={15} />
          Refresh audit
        </button>
      </div>
      {error && (
        <p className="examination-warning" role="alert">
          {error}
        </p>
      )}
      {!loaded && !error && <p role="status">Loading case audit…</p>}
      <label className="audit-filter">
        Audit event type
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="ALL">All event types</option>
          {[...new Set(rows.map((r) => r.event_type))].sort().map((t) => (
            <option key={t} value={t}>
              {readable(t)}
            </option>
          ))}
        </select>
      </label>
      {loaded && !visible.length && (
        <EmptyState title="No audit events">
          No events in this selection. Choose all event types or refresh after a
          new run.
        </EmptyState>
      )}
      {!!visible.length && (
        <div
          className="table-scroll"
          role="region"
          aria-label="Case audit history"
          tabIndex={0}
        >
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Recorded / actor</th>
                <th scope="col">Event</th>
                <th scope="col">Summary</th>
                <th scope="col">Source</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => (
                <tr key={r.id}>
                  <td>
                    {dateTime(r.timestamp)}
                    <span className="cell-subline">
                      {r.actor_id} · {readable(r.actor_role)}
                    </span>
                  </td>
                  <td>{readable(r.event_type)}</td>
                  <td>
                    {r.summary}
                    <details className="risk-details">
                      <summary>Audit detail for {r.id}</summary>
                      <pre>{JSON.stringify(r.detail, null, 2)}</pre>
                    </details>
                  </td>
                  <td>
                    <Link className="source-evidence-link" href={r.source_url}>
                      Open source #{r.source_id}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
