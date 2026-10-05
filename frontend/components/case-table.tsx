"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { Outcome, EmptyState } from "@/components/ui";
import { money } from "@/lib/format";
import type { TradeCase } from "@/types/cases";

export function CaseTable({ cases, filtered }: { cases: TradeCase[]; filtered: boolean }) {
  const router = useRouter();
  if (!cases.length) return <EmptyState title={filtered ? "No cases match these filters" : "No trade cases yet"}>{filtered ? "Adjust your search or clear the filters to return to the full register." : "Import the supplied synthetic dataset to populate the register."}</EmptyState>;
  return <div className="table-scroll" role="region" aria-label="Trade case register" tabIndex={0}>
    <table className="data-table case-table">
      <thead><tr><th scope="col">Case ID / scenario</th><th scope="col">Product</th><th scope="col">Direction</th><th scope="col" className="numeric">Amount / currency</th><th scope="col">Priority</th><th scope="col">Status</th><th scope="col">Expected outcome</th><th scope="col"><span className="sr-only">Open case</span></th></tr></thead>
      <tbody>{cases.map(item => <tr key={item.case_id} className="case-row" onClick={event => {
        if (!(event.target as HTMLElement).closest("a") && !window.getSelection()?.toString()) router.push(`/cases/${encodeURIComponent(item.case_id)}`);
      }}>
        <td className="case-identity"><Link href={`/cases/${encodeURIComponent(item.case_id)}`} className="case-link">{item.case_id}</Link><span className="cell-subline">{item.scenario || "Scenario not supplied"}</span></td>
        <td>{item.product_playbook || "Not supplied"}</td><td>{item.direction || "Not supplied"}</td>
        <td className="numeric"><span className="amount-text">{money(item.amount, item.currency, false)}</span><span className="cell-subline">{item.currency || "Not supplied"}</span></td>
        <td className="muted nowrap">{item.priority || <span title="Priority is absent from the supplied source">Not supplied</span>}</td>
        <td className="status-cell">{item.status || "Not supplied"}</td><td><Outcome value={item.expected_decision} /></td>
        <td><ArrowUpRight size={16} aria-hidden="true" className="row-arrow" /></td>
      </tr>)}</tbody>
    </table>
  </div>;
}
