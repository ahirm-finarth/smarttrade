import type {
  CaseDetail,
  CaseDocument,
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

// All document requests remain centralized here; credentials stay in the backend.
export const getCaseDocuments = (id: string) =>
  getJSON<CaseDocument[]>(`/api/v1/cases/${encodeURIComponent(id)}/documents`);

export function getDocument(id: number, versionId?: number, runId?: number) {
  const params = new URLSearchParams();
  if (versionId) params.set("version_id", String(versionId));
  if (runId) params.set("run_id", String(runId));
  return getJSON<import("@/types/documents").DocumentDetail>(
    `/api/v1/documents/${id}?${params}`,
  );
}

export class DocumentApiError extends Error {}
async function documentPost<T>(path: string, body?: FormData): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseURL}${path}`, {
      method: "POST",
      body,
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(1200000),
    });
  } catch {
    throw new DocumentApiError(
      "Connection interrupted. Refresh to check processing status before retrying.",
    );
  }
  if (!response.ok) {
    const errors: Record<number, string> = {
      404: "Document or case not found. Refresh the inventory.",
      409: "This source is already registered or processing. Refresh to check its status.",
      422: "Upload a valid, unencrypted PDF within the file and page limits.",
      503: "Document storage is temporarily unavailable. Please try again.",
    };
    throw new DocumentApiError(
      errors[response.status] || "The request failed. Refresh and try again.",
    );
  }
  return response.json() as Promise<T>;
}
export function uploadDocument(
  caseId: string,
  file: File,
  documentId?: number,
) {
  const form = new FormData();
  form.append("file", file);
  if (documentId) form.append("document_id", String(documentId));
  return documentPost<import("@/types/documents").UploadResult>(
    `/api/v1/cases/${encodeURIComponent(caseId)}/documents`,
    form,
  );
}
export function processDocument(
  id: number,
  reprocess = false,
  versionId?: number,
) {
  return documentPost<import("@/types/documents").ProcessingRun>(
    `/api/v1/documents/${id}/${reprocess ? "reprocess" : "process"}${versionId ? `?version_id=${versionId}` : ""}`,
  );
}
export const documentSourceURL = (id: number, versionId: number) =>
  `${baseURL}/api/v1/documents/${id}/source?version_id=${versionId}`;
export const documentPageURL = (id: number, versionId: number, page: number) =>
  `${baseURL}/api/v1/documents/${id}/pages/${page}/image?version_id=${versionId}`;
