import type { DashboardSummary } from "@/types/cases";

export function Metrics({ summary }: { summary: DashboardSummary }) {
  const values = [
    { label: "Total cases", value: summary.total_cases, detail: "Persisted trade cases", className: "" },
    { label: "Expected PASS", value: summary.expected_outcomes.PASS || 0, detail: "Demo reference outcome", className: "metric-pass" },
    { label: "Expected REFER", value: summary.expected_outcomes.REFER || 0, detail: "Demo reference outcome", className: "metric-refer" },
    { label: "Expected BLOCK", value: summary.expected_outcomes.BLOCK || 0, detail: "Demo reference outcome", className: "metric-block" },
  ];
  return <dl className="metrics" aria-label="Trade case summary">{values.map(item => <div key={item.label} className={`metric ${item.className}`}><dt>{item.label}</dt><dd>{item.value.toLocaleString("en-IN")}</dd><span>{item.detail}</span></div>)}</dl>;
}
