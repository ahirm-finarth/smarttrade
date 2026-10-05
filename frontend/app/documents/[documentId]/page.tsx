import { notFound } from "next/navigation";
import { ApiError, getDocument } from "@/lib/api";
import { DocumentWorkspace } from "@/components/document-workspace";

export const dynamic = "force-dynamic";
export default async function DocumentPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  if (!/^\d+$/.test(documentId)) notFound();
  let detail;
  try {
    detail = await getDocument(Number(documentId));
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  return <DocumentWorkspace initial={detail} />;
}
