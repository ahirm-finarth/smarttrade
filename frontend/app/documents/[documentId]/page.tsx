import { notFound } from "next/navigation";
import { ApiError, getDocument } from "@/lib/api";
import { DocumentWorkspace } from "@/components/document-workspace";

export const dynamic = "force-dynamic";
export default async function DocumentPage({
  params,
  searchParams,
}: {
  params: Promise<{ documentId: string }>;
  searchParams: Promise<{
    version_id?: string;
    run_id?: string;
    fact_id?: string;
  }>;
}) {
  const { documentId } = await params;
  if (!/^\d+$/.test(documentId)) notFound();
  const query = await searchParams;
  function positive(value?: string) {
    if (!value) return undefined;
    if (
      !/^\d+$/.test(value) ||
      !Number.isSafeInteger(Number(value)) ||
      Number(value) < 1
    )
      notFound();
    return Number(value);
  }
  const versionId = positive(query.version_id);
  const runId = positive(query.run_id);
  const factId = positive(query.fact_id);
  let detail;
  try {
    detail = await getDocument(Number(documentId), versionId, runId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  return <DocumentWorkspace initial={detail} initialFactId={factId} />;
}
