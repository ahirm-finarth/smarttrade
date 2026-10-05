export interface Evidence {
  fact_id: number | null;
  case_id: string;
  document_id: number;
  document_version_id: number;
  version_number: number;
  processing_run_id: number;
  processing_run_number: number;
  filename: string;
  document_type: string;
  field_name: string;
  role: string;
  raw_value: string;
  normalized_value: unknown;
  comparison_value: unknown;
  page_number: number;
  source_text: string;
  confidence: string;
  evidence_status: string;
  source_verified: boolean;
  review_reason: string | null;
  derivation: string | null;
}
export interface ResolvedSubject {
  state: string;
  reason: string;
  evidence: Evidence | null;
  candidate_fact_ids: number[];
}
export interface RuleExecution {
  id: number;
  rule_id: string;
  rule_version: number;
  comparison_type: string;
  status: string;
  rule_snapshot_json: {
    name: string;
    severity: string;
    parameters: Record<string, unknown>;
  };
  input_json: { expected: ResolvedSubject; observed: ResolvedSubject };
  output_json: { reason: string; details: Record<string, unknown> };
}
export interface Finding {
  id: number;
  rule_execution_pk: number;
  finding_type: string;
  title: string;
  description: string;
  severity: string;
  rule_id: string;
  rule_version: number;
  expected_json: Evidence;
  observed_json: Evidence;
}
export interface Relation {
  id: number;
  rule_execution_pk: number;
  relation_type: string;
  status: string;
  confidence: string;
  expected: Evidence | null;
  observed: Evidence | null;
}
export interface ExaminationRun {
  id: number;
  case_id: string;
  run_number: number;
  playbook: string;
  ruleset_version: string;
  input_fingerprint: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  summary_json: {
    rules_executed?: number;
    matched?: number;
    findings?: number;
    incomplete?: number;
    relations?: number;
    confidence_threshold?: string;
  };
}
export interface ExaminationDetail {
  run: ExaminationRun;
  executions: RuleExecution[];
  findings: Finding[];
  relations: Relation[];
  inputs_current: boolean;
}
export interface CurrentCaseEvidence {
  case_id: string;
  documents: Record<string, unknown>[];
  facts: Evidence[];
  confidence_threshold: string;
}
