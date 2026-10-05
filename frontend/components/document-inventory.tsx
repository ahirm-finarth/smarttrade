"use client";
import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Upload, RefreshCw, ArrowUpRight } from "lucide-react";
import { DataTable, EmptyState, SectionHeading } from "@/components/ui";
import {
  activeStatuses,
  DocumentStatus,
  readable,
} from "@/components/document-status";
import { getCaseDocuments, processDocument, uploadDocument } from "@/lib/api";
import { dateTime } from "@/lib/format";
import type { CaseDocument } from "@/types/cases";

export function DocumentInventory({
  caseId,
  initial,
  active,
}: {
  caseId: string;
  initial: CaseDocument[];
  active: boolean;
}) {
  const router = useRouter();
  const [documents, setDocuments] = useState(initial);
  const [pending, setPending] = useState<number | "upload" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function refresh() {
    try {
      setDocuments(await getCaseDocuments(caseId));
      setError("");
    } catch {
      setError("Inventory could not refresh. Try Refresh documents.");
    }
  }
  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    const poll = () =>
      getCaseDocuments(caseId)
        .then((rows) => {
          if (!cancelled) setDocuments(rows);
        })
        .catch(() => {
          if (!cancelled)
            setError("Inventory could not refresh. Try Refresh documents.");
        });
    void poll();
    const timer = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [active, caseId]);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get("file");
    if (!(file instanceof File) || !file.size) return;
    if (file.size > 20 * 1024 * 1024) {
      setError("Choose a PDF of 20 MB or smaller.");
      return;
    }
    setPending("upload");
    setError("");
    setMessage("Uploading source PDF…");
    try {
      const result = await uploadDocument(caseId, file);
      setMessage(
        result.duplicate
          ? "This exact PDF is already registered in this case."
          : "PDF uploaded. Open the document or select Process to extract its fields.",
      );
      form.reset();
      await refresh();
      router.refresh();
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Upload failed. Try again.",
      );
      setMessage("");
    } finally {
      setPending(null);
    }
  }
  async function process(document: CaseDocument) {
    setPending(document.id);
    setError("");
    setMessage("Processing source PDF. Stages below reflect saved progress.");
    try {
      const result = await processDocument(
        document.id,
        !!document.detected_type,
      );
      setMessage(
        result.status === "COMPLETED"
          ? "Extraction complete. Open the document to inspect its source-backed fields."
          : "",
      );
      if (result.status !== "COMPLETED")
        setError(
          result.error_message ||
            "Processing requires review. Open the document for details.",
        );
      await refresh();
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Processing failed. Refresh and try again.",
      );
      setMessage("");
    } finally {
      setPending(null);
    }
  }
  return (
    <>
      <div className="document-inventory-heading">
        <SectionHeading title="Document inventory" count={documents.length}>
          Original PDFs and their saved extraction state. Open a document to
          inspect fields and source pages.
        </SectionHeading>
        <button className="button button-secondary" onClick={refresh}>
          <RefreshCw size={14} />
          Refresh documents
        </button>
      </div>
      <form className="document-upload" onSubmit={upload}>
        <div>
          <label htmlFor={`pdf-${caseId}`}>Add a source document</label>
          <p>PDF only · up to 20 MB · originals preserved</p>
        </div>
        <input
          id={`pdf-${caseId}`}
          name="file"
          type="file"
          accept="application/pdf,.pdf"
          required
          disabled={pending !== null}
        />
        <button className="button button-primary" disabled={pending !== null}>
          <Upload size={15} />
          {pending === "upload" ? "Uploading…" : "Upload Document"}
        </button>
      </form>
      {message && (
        <p className="document-notice" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="document-notice notice-error" role="alert">
          {error}
        </p>
      )}
      {documents.length ? (
        <DataTable
          rows={documents}
          empty="No documents registered."
          columns={[
            {
              label: "Document",
              render: (d) => (
                <>
                  <Link className="document-link" href={`/documents/${d.id}`}>
                    {d.file_name || d.document_id || "Source document"}
                  </Link>
                  <span className="cell-subline">
                    {d.document_id} · Inventory:{" "}
                    {d.document_type || "Unlabelled"}
                  </span>
                </>
              ),
            },
            {
              label: "Detected type",
              render: (d) => readable(d.detected_type),
            },
            {
              label: "Version / pages",
              render: (d) =>
                d.version_number ? (
                  <>
                    v{d.version_number}
                    <span className="cell-subline">
                      {d.page_count ?? "—"}{" "}
                      {d.page_count === 1 ? "page" : "pages"}
                    </span>
                  </>
                ) : (
                  "—"
                ),
            },
            {
              label: "Processing / extraction",
              render: (d) => (
                <>
                  <DocumentStatus status={d.processing_status} />
                  <span className="cell-subline">
                    Extraction: {readable(d.extraction_status)}
                  </span>
                </>
              ),
            },
            {
              label: "Updated",
              render: (d) =>
                d.source_updated_at ? dateTime(d.source_updated_at) : "—",
            },
            {
              label: "Actions",
              render: (d) => (
                <div className="document-row-actions">
                  <button
                    className="button button-secondary"
                    disabled={
                      !d.version_number ||
                      pending !== null ||
                      activeStatuses.has(d.processing_status)
                    }
                    onClick={() => process(d)}
                  >
                    {pending === d.id || activeStatuses.has(d.processing_status)
                      ? "Processing…"
                      : d.detected_type
                        ? "Reprocess"
                        : "Process"}
                  </button>
                  <Link className="document-link" href={`/documents/${d.id}`}>
                    Open document
                    <ArrowUpRight size={13} />
                  </Link>
                  {d.detected_type && (
                    <Link
                      className="document-link"
                      href={`/documents/${d.id}#extracted-fields`}
                    >
                      View extracted data
                    </Link>
                  )}
                </div>
              ),
            },
          ]}
        />
      ) : (
        <EmptyState title="Add the first source PDF">
          Upload a document to start its intake and extraction.
        </EmptyState>
      )}
    </>
  );
}
