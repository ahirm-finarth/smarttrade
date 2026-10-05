import { getSummary } from "@/lib/api";
import { EmptyState } from "@/components/ui";

export const dynamic = "force-dynamic";
export default async function Home() {
  const summary = await getSummary();
  return <div className="page-content"><h1>Smart Trade</h1><EmptyState title="Operations workspace connected">{summary.total_cases} persisted cases are available. The dashboard is being assembled.</EmptyState></div>;
}
