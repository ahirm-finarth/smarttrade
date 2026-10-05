import type { Evidence } from "./examinations";

export interface RiskSubject {
  subject_type: string;
  subject: string | null;
  role: string | null;
  country: string | null;
  party_id: number | null;
  evidence: Evidence[];
  trade: Record<string, unknown>;
}
export interface ProviderResult {
  status: string;
  reason: string;
  synthetic: boolean;
  matched_records: {
    reference_id: string;
    reference_type: string;
    name: string;
    country: string | null;
    status: string;
    note: string;
  }[];
  details: Record<string, unknown>;
}
export interface ProviderCheck {
  id: number;
  provider_type: string;
  provider_name: string;
  provider_version: string;
  status: string;
  input_json: RiskSubject;
  result_json: ProviderResult;
  started_at: string;
  completed_at: string | null;
}
export interface RiskExecution {
  id: number;
  provider_check_pk: number;
  rule_id: string;
  rule_version: number;
  status: string;
  rule_snapshot_json: { name: string; severity: string; handler: string };
  output_json: { reason: string };
}
export interface RiskFinding {
  id: number;
  provider_check_pk: number;
  rule_execution_pk: number;
  title: string;
  category: string;
  subject_value: string;
  severity: string;
  rule_id: string;
  rule_version: number;
  description: string;
  evidence_json: {
    subject: RiskSubject;
    provider: { name: string; version: string; result: ProviderResult };
    rule: Record<string, unknown>;
    candidate: Record<string, unknown> | null;
  };
}
export interface RiskRun {
  id: number;
  case_id: string;
  run_number: number;
  ruleset_version: string;
  provider_set: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  input_fingerprint: string;
  summary_json: {
    checks: Record<string, number>;
    results_by_status: Record<string, number>;
    findings: number;
    findings_by_severity: Record<string, number>;
    rules_executed: number;
  };
}
export interface RiskDetail {
  run: RiskRun;
  checks: ProviderCheck[];
  executions: RiskExecution[];
  findings: RiskFinding[];
  inputs_current: boolean;
  synthetic: boolean;
}
