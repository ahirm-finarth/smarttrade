import type {
  CaseDetail,
  CaseList,
  CaseQuery,
  DashboardSummary,
} from "@/types/cases";

const baseURL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number) {
    super(
      status === 404
        ? "Trade case not found"
        : "Smart Trade data is temporarily unavailable",
    );
  }
}

async function getJSON<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseURL}${path}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new ApiError(503);
  }
  if (!response.ok) throw new ApiError(response.status);
  return response.json() as Promise<T>;
}

export const getSummary = () =>
  getJSON<DashboardSummary>("/api/v1/dashboard/summary");
export function getCases(query: CaseQuery = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return getJSON<CaseList>(`/api/v1/cases?${params.toString()}`);
}
export const getCase = (id: string) =>
  getJSON<CaseDetail>(`/api/v1/cases/${encodeURIComponent(id)}`);
