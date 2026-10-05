"use client";
import { useState, type KeyboardEvent } from "react";
import { ArrowRight, FileText, Users, ListChecks, ShieldAlert, History, Rows3 } from "lucide-react";
import { DataTable, SectionHeading, supplied } from "@/components/ui";
import { money, dateTime } from "@/lib/format";
import type { CaseDetail } from "@/types/cases";

const tabs = [
  { id: "overview", label: "Overview" }, { id: "parties", label: "Parties" },
  { id: "documents", label: "Documents" }, { id: "trade_lines", label: "Trade lines" },
  { id: "discrepancies", label: "Discrepancies" }, { id: "risk_events", label: "Risk events" },
  { id: "approvals", label: "Approvals" },
] as const;
type Tab = typeof tabs[number]["id"];

export function CaseWorkspace({ tradeCase: data }: { tradeCase: CaseDetail }) {
  const [active, setActive] = useState<Tab>("overview");
  const inventory = [
    { id: "parties", label: "Parties", count: data.parties.length, icon: Users },
    { id: "documents", label: "Documents", count: data.documents.length, icon: FileText },
    { id: "trade_lines", label: "Trade lines", count: data.trade_lines.length, icon: Rows3 },
    { id: "discrepancies", label: "Discrepancies", count: data.discrepancies.length, icon: ListChecks },
    { id: "risk_events", label: "Risk events", count: data.risk_events.length, icon: ShieldAlert },
    { id: "approvals", label: "Approval events", count: data.approvals.length, icon: History },
  ] as const;
  function selectTab(tab: Tab, focus = false) {
    setActive(tab);
    if (focus) document.getElementById(`tab-${tab}`)?.focus();
  }
  function keyboard(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let target: number;
    if (event.key === "ArrowRight") target = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") target = (index + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") target = 0;
    else if (event.key === "End") target = tabs.length - 1;
    else return;
    event.preventDefault(); selectTab(tabs[target].id, true);
  }
  return <section className="workspace" aria-label="Trade case workspace">
    <div className="workspace-tabs" role="tablist" aria-label="Case sections">{tabs.map((tab, index) => <button key={tab.id} role="tab" id={`tab-${tab.id}`} aria-selected={active === tab.id} aria-controls={`panel-${tab.id}`} tabIndex={active === tab.id ? 0 : -1} onClick={() => selectTab(tab.id)} onKeyDown={event => keyboard(event, index)}>{tab.label}{tab.id !== "overview" && <span>{data[tab.id].length}</span>}</button>)}</div>
    {tabs.map(tab => <div key={tab.id} role="tabpanel" id={`panel-${tab.id}`} aria-labelledby={`tab-${tab.id}`} hidden={active !== tab.id} tabIndex={0} className="workspace-panel">
      {tab.id === "overview" && <>
        <SectionHeading title="Case overview">Source metadata and related synthetic records.</SectionHeading>
        <div className="overview-grid"><div><h3>Demo narrative</h3><p className="narrative">{data.demo_narrative || "No narrative was supplied for this case."}</p><dl className="metadata-list">
          <div><dt>Applicant</dt><dd>{supplied(data.applicant)}</dd></div><div><dt>Beneficiary</dt><dd>{supplied(data.beneficiary)}</dd></div>
          <div><dt>Customer ID</dt><dd>{supplied(data.customer_id)}</dd></div><div><dt>Facility ID</dt><dd>{supplied(data.facility_id)}</dd></div>
          <div><dt>Record created</dt><dd>{dateTime(data.created_at)}</dd></div><div><dt>Record updated</dt><dd>{dateTime(data.updated_at)}</dd></div>
        </dl><p className="source-footnote">Record timestamps describe persistence. Empty fields were not supplied in the source.</p></div>
        <div className="inventory"><h3>Related records</h3>{inventory.map(item => <button key={item.id} onClick={() => selectTab(item.id, true)}><item.icon size={16} /><span>{item.label}</span><strong>{item.count}</strong><ArrowRight size={14} /></button>)}</div></div>
      </>}
      {tab.id === "parties" && <>
        <SectionHeading title="Parties" count={data.parties.length}>Roles and screening statuses from the synthetic source. No live screening is performed.</SectionHeading>
        <DataTable rows={data.parties} empty="No party records were supplied for this case." columns={[
          { label: "Role", render: r => supplied(r.party_role) }, { label: "Party name", render: r => supplied(r.party_name) },
          { label: "Country", render: r => supplied(r.country) }, { label: "Demo screening status", render: r => supplied(r.screening_status) },
        ]} />
      </>}
      {tab.id === "documents" && <>
        <SectionHeading title="Document inventory" count={data.documents.length}>Supplied document metadata only. Source confidence is a demo reference; no files are extracted or examined.</SectionHeading>
        <DataTable rows={data.documents} empty="No document inventory was supplied for this case." columns={[
          { label: "Document / ID", render: r => <>{supplied(r.document_type)}<span className="cell-subline">{r.document_id}</span></> },
          { label: "Reference", render: r => supplied(r.reference) }, { label: "File name", render: r => <span className="filename">{supplied(r.file_name)}</span> },
          { label: "Expected", render: r => r.expected === null ? "Not supplied" : r.expected ? "Yes" : "No" },
          { label: "Received", render: r => r.received === null ? "Not supplied" : r.received ? "Yes" : "No" },
          { label: "Source confidence", render: r => r.extraction_confidence === null ? "Not supplied" : `${(Number(r.extraction_confidence) * 100).toFixed(0)}%`, className: "numeric" },
        ]} />
      </>}
      {tab.id === "trade_lines" && <>
        <SectionHeading title="Trade lines" count={data.trade_lines.length}>Item-level values as supplied. Amounts remain in their source currency.</SectionHeading>
        <DataTable rows={data.trade_lines} empty="No trade lines were supplied for this case." columns={[
          { label: "Source", render: r => supplied(r.source) }, { label: "Item", render: r => supplied(r.item_no) },
          { label: "Goods", render: r => supplied(r.goods_description) }, { label: "Quantity", render: r => supplied(r.quantity), className: "numeric" },
          { label: "Unit", render: r => supplied(r.uom) }, { label: "Unit price", render: r => money(r.unit_price, r.currency), className: "numeric" },
          { label: "Line amount", render: r => money(r.line_amount, r.currency), className: "numeric" },
        ]} />
      </>}
      {tab.id === "discrepancies" && <>
        <SectionHeading title="Discrepancies" count={data.discrepancies.length}>Historical demo findings from the source. Phase 1 does not perform documentary examination.</SectionHeading>
        <DataTable rows={data.discrepancies} empty="No discrepancy records were supplied for this case. This is not a computed examination result." columns={[
          { label: "Finding / source rule", render: r => <>{supplied(r.finding_id)}<span className="cell-subline">{r.rule_id}</span></> },
          { label: "Severity / category", render: r => <>{supplied(r.severity)}<span className="cell-subline">{r.category}</span></> },
          { label: "Field", render: r => supplied(r.field) }, { label: "Expected value", render: r => supplied(r.expected_value) },
          { label: "Observed value", render: r => supplied(r.observed_value) }, { label: "Source evidence reference", render: r => supplied(r.evidence) },
          { label: "Route / status", render: r => <>{supplied(r.route_to)}<span className="cell-subline">{r.status}</span></> },
        ]} />
      </>}
      {tab.id === "risk_events" && <>
        <SectionHeading title="Risk events" count={data.risk_events.length}>Supplied synthetic signals. Provider names and results are demo references; no live checks are performed.</SectionHeading>
        <DataTable rows={data.risk_events} empty="No risk event records were supplied for this case. No screening conclusion is implied." columns={[
          { label: "Risk / ID", render: r => <>{supplied(r.risk_type)}<span className="cell-subline">{r.risk_id}</span></> },
          { label: "Subject", render: r => supplied(r.subject) }, { label: "Demo provider", render: r => supplied(r.provider) },
          { label: "Source result", render: r => supplied(r.result) }, { label: "Severity", render: r => supplied(r.severity) },
          { label: "Reason", render: r => supplied(r.reason) },
        ]} />
      </>}
      {tab.id === "approvals" && <>
        <SectionHeading title="Approval history" count={data.approvals.length}>Read-only events supplied by the synthetic dataset. Timestamps shown in IST; no approval actions are available.</SectionHeading>
        <DataTable rows={data.approvals} empty="No historical approval events were supplied for this case." columns={[
          { label: "Event time", render: r => dateTime(r.event_time) },
          { label: "Actor / role", render: r => <>{supplied(r.actor_role)}<span className="cell-subline">{r.actor_id}</span></> },
          { label: "Source action", render: r => supplied(r.action) }, { label: "Source outcome", render: r => supplied(r.outcome) },
        ]} />
      </>}
    </div>)}
  </section>;
}
