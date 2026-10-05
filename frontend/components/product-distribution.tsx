import { EmptyState } from "@/components/ui";
import type { DashboardSummary } from "@/types/cases";

export function ProductDistribution({ summary }: { summary: DashboardSummary }) {
  return <section className="product-panel" aria-labelledby="products-title"><div className="product-heading"><h2 id="products-title">Product distribution</h2><span className="muted">{summary.product_distribution.length} products in the register</span></div>
    {!summary.total_cases ? <EmptyState title="Product mix will appear here">Import trade cases to see the products represented in the register.</EmptyState> : <>
      <div className="distribution-bar" aria-hidden="true">{summary.product_distribution.map((item, i) => <span key={item.product ?? "unspecified"} className={`product-tone tone-${i % 4}`} style={{ width: `${item.count / summary.total_cases * 100}%` }} />)}</div>
      <ul className="product-legend">{summary.product_distribution.map((item, i) => <li key={item.product ?? "unspecified"}><span className={`legend-dot product-tone tone-${i % 4}`} /><span>{item.product || "Not supplied"}</span><strong>{item.count}</strong><span className="muted">{item.count === 1 ? "case" : "cases"}</span></li>)}</ul>
    </>}
  </section>;
}
