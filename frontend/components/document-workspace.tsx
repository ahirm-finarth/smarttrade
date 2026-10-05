"use client";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowUpRight,
  FileText,
  RefreshCw,
  Play,
  Upload,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  activeStatuses,
  DocumentStatus,
  readable,
} from "@/components/document-status";
import { EmptyState } from "@/components/ui";
import {
  documentPageURL,
  documentSourceURL,
  getDocument,
  processDocument,
  uploadDocument,
} from "@/lib/api";
import { dateTime } from "@/lib/format";
import type { DocumentDetail, ExtractedFact } from "@/types/documents";

function displayValue(fact: ExtractedFact) {
  const value = fact.normalized_json;
  if (value && typeof value === "object") {
    const structured = value as Record<string, string>;
    if (structured.amount) return `${structured.currency} ${structured.amount}`;
    if (structured.quantity) return `${structured.quantity} ${structured.unit}`;
  }
  return fact.normalized_value || fact.raw_value;
}
function HighlightedText({ text, value }: { text: string; value?: string }) {
  const start = value ? text.indexOf(value) : -1;
  if (start < 0 || !value) return <>{text}</>;
  return (
    <>
      {text.slice(0, start)}
      <mark>{value}</mark>
      {text.slice(start + value.length)}
    </>
  );
}

export function DocumentWorkspace({ initial }: { initial: DocumentDetail }) {
  const [data, setData] = useState(initial);
  const [factId, setFactId] = useState<number | null>(
    initial.facts[0]?.id ?? null,
  );
  const [page, setPage] = useState(initial.facts[0]?.page_number ?? 1);
  const [busy, setBusy] = useState(false);
  const [operation, setOperation] = useState<"process" | "upload" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [imageError, setImageError] = useState(false);
  const requestSequence = useRef(0);
  const version = data.selected_version;
  const run = data.selected_run;
  const fact = data.facts.find((candidate) => candidate.id === factId) ?? null;
  const pageText = data.pages.find(
    (candidate) => candidate.page_number === page,
  );
  const status = run?.status || version?.status || "NOT_REGISTERED";
  const running = activeStatuses.has(status);
  const processing = busy && operation === "process";
  const id = data.document.id;
  const versionId = version?.id;
  const refresh = useCallback(
    async (
      selectedVersion?: number,
      selectedRun?: number,
      resetFact = false,
    ) => {
      const sequence = ++requestSequence.current;
      try {
        const next = await getDocument(id, selectedVersion, selectedRun);
        if (sequence !== requestSequence.current) return;
        setData(next);
        setError("");
        if (resetFact) {
          setFactId(next.facts[0]?.id ?? null);
          setPage(next.facts[0]?.page_number ?? 1);
          setImageError(false);
        }
      } catch {
        if (sequence === requestSequence.current)
          setError("Document could not refresh. Select Refresh to try again.");
      }
    },
    [id],
  );
  useEffect(() => {
    if (!running && !busy) return;
    const timer = setInterval(() => {
      void refresh(versionId);
    }, 2500);
    return () => clearInterval(timer);
  }, [running, busy, refresh, versionId]);
  async function process() {
    if (!version) return;
    ++requestSequence.current;
    setBusy(true);
    setOperation("process");
    setError("");
    setMessage("Processing PDF. The status reflects saved stages.");
    try {
      const result = await processDocument(id, !!run, version.id);
      await refresh(version.id, result.id, true);
      setMessage(
        result.status === "COMPLETED"
          ? "Extraction complete. Select a field to inspect its source."
          : "",
      );
      if (result.status !== "COMPLETED")
        setError(result.error_message || "Extraction needs review.");
    } catch (error) {
      ++requestSequence.current;
      setError(
        error instanceof Error
          ? error.message
          : "Processing failed. Refresh to check its status.",
      );
      setMessage("");
    } finally {
      setBusy(false);
    }
  }
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get("file");
    if (!(file instanceof File) || !file.size) return;
    if (file.size > 20 * 1024 * 1024) {
      setError("Choose a PDF of 20 MB or smaller.");
      return;
    }
    ++requestSequence.current;
    setBusy(true);
    setOperation("upload");
    setError("");
    try {
      const result = await uploadDocument(data.case_id, file, id);
      await refresh(result.version.id, undefined, true);
      setMessage(
        result.duplicate
          ? "This exact source is already registered."
          : "New immutable version uploaded. Select Process to extract it.",
      );
      form.reset();
    } catch (error) {
      ++requestSequence.current;
      setError(
        error instanceof Error ? error.message : "Upload failed. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  function selectFact(selected: ExtractedFact) {
    setFactId(selected.id);
    setPage(selected.page_number);
    setImageError(false);
  }
  return (
    <div className="page-content document-content">
      <Link
        className="back-link"
        href={`/cases/${encodeURIComponent(data.case_id)}?tab=documents`}
      >
        <ArrowLeft size={15} />
        Back to case documents
      </Link>
      <div className="document-heading">
        <div>
          <h1>
            {version?.original_filename ||
              data.document.file_name ||
              "Source document"}
          </h1>
          <p>
            {data.case_id} · {readable(run?.document_type || null)}
            {run?.classification_confidence
              ? ` · Classification ${Math.round(Number(run.classification_confidence) * 100)}%`
              : ""}
          </p>
        </div>
        <div className="document-heading-actions">
          <button
            className="button button-secondary"
            onClick={() => {
              setImageError(false);
              void refresh(versionId, run?.id);
            }}
            disabled={busy}
          >
            <RefreshCw size={14} />
            Refresh
          </button>
          <button
            className="button button-primary"
            onClick={process}
            disabled={!version || busy || running}
          >
            {run ? <RefreshCw size={14} /> : <Play size={14} />}
            {processing || running
              ? "Processing…"
              : run
                ? "Reprocess"
                : "Process"}
          </button>
        </div>
      </div>
      {data.is_synthetic && (
        <p className="document-demo">
          Synthetic demonstration · Not a financial instrument
        </p>
      )}
      <div className="document-toolbar">
        <DocumentStatus status={status} />
        <label>
          Version
          <select
            aria-label="Document version"
            disabled={busy || running}
            value={version?.id || ""}
            onChange={(event) =>
              refresh(Number(event.target.value), undefined, true)
            }
          >
            {data.versions.map((v) => (
              <option key={v.id} value={v.id}>
                v{v.version_number} · {dateTime(v.created_at)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Extraction run
          <select
            aria-label="Extraction run"
            disabled={busy || running || !run}
            value={run?.id || ""}
            onChange={(event) =>
              refresh(undefined, Number(event.target.value), true)
            }
          >
            {!run && <option value="">Not processed</option>}
            {data.processing_runs
              .filter((r) => r.document_version_pk === versionId)
              .map((r) => (
                <option key={r.id} value={r.id}>
                  Run {r.run_number} · {readable(r.status)}
                </option>
              ))}
          </select>
        </label>
        {version && (
          <a
            className="document-link"
            href={documentSourceURL(id, version.id)}
            target="_blank"
            rel="noreferrer"
          >
            Open original PDF
            <ArrowUpRight size={14} />
          </a>
        )}
      </div>
      {message && (
        <p role="status" className="document-notice">
          {message}
        </p>
      )}
      {(error || run?.error_message) && (
        <p role="alert" className="document-notice notice-error">
          {error || run?.error_message}
        </p>
      )}
      {!version ? (
        <EmptyState title="Source PDF not registered">
          Upload the source below, or register the supplied demo packet using
          the developer command.
        </EmptyState>
      ) : (
        <div className="document-desk">
          <section
            className="source-pane"
            id="source-page"
            aria-label="Source PDF page"
          >
            <div className="document-pane-heading">
              <h2>
                <FileText size={17} />
                Source PDF
              </h2>
              <div className="page-controls">
                <button
                  className="button button-secondary"
                  aria-label="Previous source page"
                  disabled={page <= 1}
                  onClick={() => {
                    setPage(page - 1);
                    setImageError(false);
                  }}
                >
                  <ChevronLeft size={15} />
                </button>
                <label>
                  Page
                  <select
                    aria-label="Source page"
                    value={page}
                    onChange={(event) => {
                      setPage(Number(event.target.value));
                      setImageError(false);
                    }}
                  >
                    {Array.from(
                      { length: version.page_count || 1 },
                      (_, index) => (
                        <option key={index} value={index + 1}>
                          {index + 1}
                        </option>
                      ),
                    )}
                  </select>
                </label>
                <span>of {version.page_count || "—"}</span>
                <button
                  className="button button-secondary"
                  aria-label="Next source page"
                  disabled={page >= (version.page_count || 1)}
                  onClick={() => {
                    setPage(page + 1);
                    setImageError(false);
                  }}
                >
                  <ChevronRight size={15} />
                </button>
              </div>
            </div>
            <div className="pdf-canvas">
              {imageError ? (
                <EmptyState title="Page preview unavailable">
                  Use Open original PDF to inspect the source, or refresh to
                  retry.
                </EmptyState>
              ) : (
                // Native page rendering preserves the original layout without a PDF-viewer dependency.
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={`${version.id}-${page}`}
                  src={documentPageURL(id, version.id, page)}
                  alt={`${version.original_filename}, source page ${page}`}
                  onError={() => setImageError(true)}
                />
              )}
            </div>
            <details className="source-transcript" open>
              <summary>Native text · page {page}</summary>
              <pre>
                {pageText ? (
                  <HighlightedText
                    text={pageText.text_content}
                    value={
                      fact?.page_number === page ? fact.raw_value : undefined
                    }
                  />
                ) : (
                  "Page text is available after processing. No OCR text is inferred."
                )}
              </pre>
            </details>
          </section>
          <section
            className="facts-pane"
            id="extracted-fields"
            aria-label="Extracted document fields"
          >
            <div className="document-pane-heading">
              <h2>
                Extracted fields
                <span className="count-badge">{data.facts.length}</span>
              </h2>
            </div>
            <p className="facts-intro">
              Select a field to see its value and source evidence. Source
              matched means the quotation appears in the saved page text.
            </p>
            {data.facts.length ? (
              <div className="fact-list" aria-label="Choose an extracted field">
                {data.facts.map((candidate) => (
                  <button
                    key={candidate.id}
                    className="fact-option"
                    aria-pressed={factId === candidate.id}
                    onClick={() => selectFact(candidate)}
                  >
                    <span>
                      <strong>{readable(candidate.field_name)}</strong>
                      <span className="fact-value">
                        {displayValue(candidate)}
                      </span>
                    </span>
                    <span className="fact-option-meta">
                      Page {candidate.page_number}
                      <DocumentStatus status={candidate.evidence_status} />
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState
                title={
                  running || processing
                    ? "Extraction in progress"
                    : "No extracted fields yet"
                }
              >
                {running || processing
                  ? "Saved stages update automatically. Fields appear when processing finishes."
                  : "Select Process to extract fields from this source PDF. Review or failed runs do not imply successful extraction."}
              </EmptyState>
            )}
            {fact && (
              <section
                className="fact-evidence"
                aria-label="Selected field provenance"
              >
                <h3>{readable(fact.field_name)}</h3>
                <DocumentStatus status={fact.evidence_status} />
                {fact.review_reason && (
                  <p className="notice-error">{fact.review_reason}</p>
                )}
                <dl className="evidence-values">
                  <div>
                    <dt>Normalized value</dt>
                    <dd>
                      {fact.normalized_value
                        ? displayValue(fact)
                        : "Normalization requires review"}
                    </dd>
                  </div>
                  <div>
                    <dt>Raw source value</dt>
                    <dd>{fact.raw_value}</dd>
                  </div>
                  <div>
                    <dt>Source document</dt>
                    <dd>{version.original_filename}</dd>
                  </div>
                  <div>
                    <dt>Provenance</dt>
                    <dd>
                      Version {version.version_number} · Page {fact.page_number}{" "}
                      · Run {run?.run_number}
                    </dd>
                  </div>
                  <div>
                    <dt>Extraction confidence</dt>
                    <dd>{Math.round(Number(fact.confidence) * 100)}%</dd>
                  </div>
                </dl>
                <h4>Source quotation</h4>
                <blockquote>{fact.source_text}</blockquote>
                <a
                  className="document-link"
                  href="#source-page"
                  onClick={() => {
                    setPage(fact.page_number);
                    setImageError(false);
                  }}
                >
                  View source page {fact.page_number}
                  <ArrowUpRight size={14} />
                </a>
              </section>
            )}
          </section>
        </div>
      )}
      <details className="document-history">
        <summary>Source details and new version</summary>
        {version && (
          <dl className="metadata-list">
            <div>
              <dt>File size</dt>
              <dd>{(version.file_size_bytes / 1024).toFixed(1)} KB</dd>
            </div>
            <div>
              <dt>SHA-256</dt>
              <dd className="hash-value">{version.sha256}</dd>
            </div>
            <div>
              <dt>Last updated</dt>
              <dd>{dateTime(version.updated_at)}</dd>
            </div>
            {run && (
              <div>
                <dt>Processing assets</dt>
                <dd>
                  {run.parser} ·{" "}
                  {String(run.metadata_json.classification_prompt || "—")} ·{" "}
                  {String(run.metadata_json.extraction_prompt || "—")}
                </dd>
              </div>
            )}
          </dl>
        )}
        <form className="document-upload" onSubmit={upload}>
          <div>
            <label htmlFor="version-file">
              {version ? "Upload a new version" : "Add the source PDF"}
            </label>
            <p>PDF only · up to 20 MB · previous versions remain available</p>
          </div>
          <input
            id="version-file"
            name="file"
            type="file"
            accept="application/pdf,.pdf"
            required
            disabled={busy || running}
          />
          <button
            className="button button-secondary"
            disabled={busy || running}
          >
            <Upload size={14} />
            Upload PDF
          </button>
        </form>
      </details>
    </div>
  );
}
