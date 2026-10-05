import type { CaseDocument } from "./cases";

export interface DocumentVersion {
  id: number;
  document_pk: number;
  version_number: number;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256: string;
  status: string;
  page_count: number | null;
  created_at: string;
  updated_at: string;
}
export interface DocumentPage {
  id: number;
  page_number: number;
  text_content: string;
  text_length: number;
  extraction_method: string;
  needs_review: boolean;
}
export interface ProcessingRun {
  id: number;
  document_version_pk: number;
  run_number: number;
  status: string;
  parser: string;
  llm_model: string | null;
  document_type: string | null;
  classification_confidence: string | null;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  metadata_json: Record<string, unknown>;
}
export interface ExtractedFact {
  id: number;
  processing_run_pk: number;
  field_name: string;
  raw_value: string;
  normalized_value: string | null;
  normalized_json: unknown;
  page_number: number;
  source_text: string;
  confidence: string;
  evidence_status: string;
  review_reason: string | null;
  created_at: string;
}
export interface DocumentDetail {
  document: CaseDocument;
  case_id: string;
  is_synthetic: boolean;
  versions: DocumentVersion[];
  selected_version: DocumentVersion | null;
  pages: DocumentPage[];
  processing_runs: ProcessingRun[];
  selected_run: ProcessingRun | null;
  facts: ExtractedFact[];
}
export interface UploadResult {
  document_id: number;
  version: DocumentVersion;
  duplicate: boolean;
}
