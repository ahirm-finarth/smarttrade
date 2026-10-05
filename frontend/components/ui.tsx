import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

export function Outcome({ value }: { value: string | null }) {
  const kind = value && ["PASS", "REFER", "BLOCK"].includes(value) ? value.toLowerCase() : "neutral";
  return <span className={`outcome outcome-${kind}`}>{value || "Not supplied"}</span>;
}
export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return <div className="empty-state"><Inbox size={26} /><h3>{title}</h3><p>{children}</p></div>;
}
export function SectionHeading({ title, count, children }: { title: string; count?: number; children?: ReactNode }) {
  return <div className="section-heading"><div><h2>{title}{count !== undefined && <span className="count-badge">{count}</span>}</h2>{children && <p>{children}</p>}</div></div>;
}
export interface Column<T> { label: string; render: (row: T) => ReactNode; className?: string; }
export function DataTable<T extends { id: number }>({ rows, columns, empty }: { rows: T[]; columns: Column<T>[]; empty: string }) {
  if (!rows.length) return <EmptyState title="No records supplied">{empty}</EmptyState>;
  return <div className="table-scroll" role="region" aria-label="Record inventory" tabIndex={0}><table className="data-table"><thead><tr>{columns.map(col => <th key={col.label} scope="col" className={col.className}>{col.label}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.id}>{columns.map(col => <td key={col.label} className={col.className}>{col.render(row)}</td>)}</tr>)}</tbody></table></div>;
}
export const supplied = (value: string | number | null) => value ?? <span className="muted">Not supplied</span>;
