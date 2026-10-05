import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Info } from "lucide-react";
import { ApiError, getCase } from "@/lib/api";
import { money } from "@/lib/format";
import { Outcome } from "@/components/ui";
import { CaseWorkspace } from "@/components/case-workspace";

export const dynamic = "force-dynamic";
export default async function CasePage({
  params,
  searchParams,
}: {
  params: Promise<{ caseId: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { caseId } = await params;
  const { tab } = await searchParams;
  let tradeCase;
  try {
    tradeCase = await getCase(caseId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  return (
    <div className="page-content">
      <Link href="/#case-register" className="back-link">
        <ArrowLeft size={15} />
        Back to case register
      </Link>
      <div className="case-heading">
        <div>
          <h1>{tradeCase.case_id}</h1>
          <p>{tradeCase.scenario || "Trade case workspace"}</p>
        </div>
        <div className="case-reference">
          <span>Expected outcome</span>
          <Outcome value={tradeCase.expected_decision} />
        </div>
      </div>
      <dl className="case-facts">
        <div>
          <dt>Product</dt>
          <dd>{tradeCase.product_playbook || "Not supplied"}</dd>
        </div>
        <div>
          <dt>Direction</dt>
          <dd>{tradeCase.direction || "Not supplied"}</dd>
        </div>
        <div>
          <dt>Priority</dt>
          <dd>{tradeCase.priority || "Not supplied"}</dd>
        </div>
        <div>
          <dt>Amount / currency</dt>
          <dd className="numeric">
            {money(tradeCase.amount, tradeCase.currency)}
          </dd>
        </div>
      </dl>
      <div className="case-status">
        <span>Source status</span>
        <strong>{tradeCase.status || "Not supplied"}</strong>
      </div>
      {tradeCase.is_synthetic && (
        <div className="reference-note">
          <Info size={15} />
          <p>
            Synthetic case. Expected outcomes, reference findings, risks and
            approval events are supplied demo records. Documentary examinations
            use extracted source facts.
          </p>
        </div>
      )}
      <CaseWorkspace
        tradeCase={tradeCase}
        initialTab={
          tab === "documents" || tab === "examination" ? tab : "overview"
        }
      />
    </div>
  );
}
