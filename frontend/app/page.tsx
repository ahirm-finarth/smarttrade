import Link from "next/link";
import { ArrowLeft, ArrowRight, Search, Info } from "lucide-react";
import { getCases, getSummary } from "@/lib/api";
import { Metrics } from "@/components/metrics";
import { ProductDistribution } from "@/components/product-distribution";
import { CaseTable } from "@/components/case-table";
import { RefreshButton } from "@/components/refresh-button";

export const dynamic = "force-dynamic";
export default async function Dashboard({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const read = (key: string) =>
    typeof params[key] === "string" ? (params[key] as string) : "";
  const q = read("q").slice(0, 200);
  const product = read("product").slice(0, 100);
  const outcome = read("outcome").slice(0, 16);
  const numericOffset = Number(read("offset"));
  const offset =
    Number.isSafeInteger(numericOffset) && numericOffset >= 0
      ? numericOffset
      : 0;
  const limit = 20;
  const [summary, cases] = await Promise.all([
    getSummary(),
    getCases({ q, product, outcome, offset, limit }),
  ]);
  const filtered = Boolean(q || product || outcome);
  function pageURL(nextOffset: number) {
    const search = new URLSearchParams({
      q,
      product,
      outcome,
      offset: String(nextOffset),
    });
    return `/?${search.toString()}#case-register`;
  }
  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <h1>Trade dashboard</h1>
          <p>Your trade cases, in one clear view.</p>
        </div>
        <RefreshButton />
      </div>
      <Metrics summary={summary} />
      <div className="reference-note">
        <Info size={15} aria-hidden="true" />
        <p>
          Expected outcomes are supplied synthetic references. Phase 1 does not
          calculate trade decisions.
        </p>
      </div>
      <ProductDistribution summary={summary} />
      <section
        className="register"
        id="case-register"
        aria-labelledby="register-title"
      >
        <div className="register-heading">
          <div>
            <h2 id="register-title">
              Case register<span className="count-badge">{cases.total}</span>
            </h2>
            <p>Open a case to inspect its metadata and related demo records.</p>
          </div>
          <span className="register-scope">
            {summary.synthetic_cases} synthetic cases
          </span>
        </div>
        <form className="filter-bar" action="/" method="get">
          <div className="search-field">
            <Search size={16} aria-hidden="true" />
            <label className="sr-only" htmlFor="case-search">
              Search case ID or party
            </label>
            <input
              id="case-search"
              name="q"
              placeholder="Search case ID or party…"
              defaultValue={q}
              maxLength={200}
            />
          </div>
          <div className="filter-field">
            <label className="sr-only" htmlFor="product-filter">
              Filter by product
            </label>
            <select id="product-filter" name="product" defaultValue={product}>
              <option value="">All products</option>
              {summary.product_distribution
                .filter((item) => item.product)
                .map((item) => (
                  <option key={item.product!} value={item.product!}>
                    {item.product}
                  </option>
                ))}
            </select>
          </div>
          <div className="filter-field">
            <label className="sr-only" htmlFor="outcome-filter">
              Filter by expected outcome
            </label>
            <select id="outcome-filter" name="outcome" defaultValue={outcome}>
              <option value="">All expected outcomes</option>
              {Object.keys(summary.expected_outcomes).map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
          <button className="button" type="submit">
            Apply filters
          </button>
          {filtered && (
            <Link href="/#case-register" className="clear-link">
              Clear
            </Link>
          )}
        </form>
        <CaseTable cases={cases.items} filtered={filtered} />
        <div className="register-footer">
          <span>
            {cases.total
              ? `${offset + (cases.items.length ? 1 : 0)}–${offset + cases.items.length} of ${cases.total} cases`
              : "0 cases"}
          </span>
          <div className="pagination">
            {offset > 0 && (
              <Link
                className="button button-secondary"
                href={pageURL(Math.max(0, offset - limit))}
              >
                <ArrowLeft size={14} />
                Previous
              </Link>
            )}
            {offset + cases.items.length < cases.total && (
              <Link
                className="button button-secondary"
                href={pageURL(offset + limit)}
              >
                Next
                <ArrowRight size={14} />
              </Link>
            )}
          </div>
          <span>Amounts shown in their source currency</span>
        </div>
      </section>
    </div>
  );
}
