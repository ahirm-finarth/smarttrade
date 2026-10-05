import type { Evidence } from "./examinations";

export interface DemoActor {
  actor_id: string;
  display_name: string;
  roles: string[];
}
export interface DecisionRun {
  id: number;
  case_id: string;
  run_number: number;
  examination_run_pk: number | null;
  risk_run_pk: number | null;
  ruleset_version: string;
  status: string;
  recommended_decision: string | null;
  input_fingerprint: string;
  summary_json: {
    reasons: number;
    blocking_reasons: number;
    optional_unchecked: number;
    documentary_findings: number;
    risk_findings: number;
    required_approvals: string[];
  };
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}
export interface DecisionReason {
  id: number;
  decision_run_pk: number;
  reason_type: string;
  reason_code: string;
  impact: string;
  severity: string;
  source_status: string;
  title: string;
  route_to: string | null;
  documentary_finding_pk: number | null;
  risk_finding_pk: number | null;
  examination_execution_pk: number | null;
  provider_check_pk: number | null;
  evidence_json: Record<string, unknown>;
}
export interface GovernedWorkflow {
  id: number;
  state: string;
  final_outcome: string | null;
  maker_actor_id: string | null;
  checker_actor_id: string | null;
  revision: number;
  finalized_at: string | null;
}
export interface WorkflowTask {
  id: number;
  decision_run_pk: number;
  task_type: string;
  assigned_role: string;
  assigned_actor_id: string | null;
  status: string;
  priority: string;
  title: string;
  description: string;
  reason_ids_json: number[];
  resolution: string | null;
  created_at: string;
  completed_at: string | null;
  available_actions: string[];
}
export interface WorkflowEvent {
  id: number;
  task_pk: number | null;
  event_type: string;
  actor_id: string;
  actor_role: string;
  comment: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}
export interface DecisionOverride {
  id: number;
  actor_id: string;
  actor_role: string;
  from_decision: string;
  to_decision: string;
  rationale: string;
  reason_ids_json: number[];
  evidence_reference: string | null;
  previous_outcome: string | null;
  created_at: string;
}
export interface FindingResolution {
  id: number;
  decision_reason_pk: number;
  task_pk: number;
  resolution: string;
  rationale: string;
  actor_id: string;
  actor_role: string;
  created_at: string;
}
export interface DecisionDetail {
  run: DecisionRun;
  input_snapshot: {
    documentary: { id: number; run_number: number; status: string } | null;
    risk: { id: number; run_number: number; status: string } | null;
    policy: {
      version: string;
      mandatory_categories: string[];
      optional_categories: string[];
      required_approvals: string[];
      overrideable_codes: string[];
      financing_event_control_mandatory: boolean;
    };
    routing_policy: { version: string };
  };
  reasons: DecisionReason[];
  workflow: GovernedWorkflow | null;
  tasks: WorkflowTask[];
  events: WorkflowEvent[];
  overrides: DecisionOverride[];
  resolutions: FindingResolution[];
  inputs_current: boolean;
  effective_final_outcome: string | null;
  unresolved_reason_ids: number[];
  maker_actor_ids: string[];
  demo_actor: DemoActor;
  demo_only: boolean;
}
export interface ExceptionAdvice {
  executive_summary: string;
  grouped_issues: { label: string; reason_ids: number[] }[];
  suggested_queue: string;
  draft_reviewer_note: string;
  draft_information_request: string;
}
export interface AdvisoryResponse {
  advisory: boolean;
  decision_id: number;
  event_id: number;
  output: ExceptionAdvice;
}
export interface AuditEntry {
  id: string;
  timestamp: string;
  event_type: string;
  actor_id: string;
  actor_role: string;
  summary: string;
  source_url: string;
  source_id: number;
  detail: Record<string, unknown>;
}

export function sourceEvidence(reason: DecisionReason): Evidence[] {
  const found = new Map<string, Evidence>();
  function visit(value: unknown) {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== "object") return;
    const row = value as Record<string, unknown>;
    if (
      typeof row.document_id === "number" &&
      typeof row.source_text === "string" &&
      typeof row.raw_value === "string" &&
      typeof row.page_number === "number"
    ) {
      const evidence = row as unknown as Evidence;
      found.set(
        `${evidence.document_version_id}:${evidence.processing_run_id}:${evidence.fact_id}`,
        evidence,
      );
    } else Object.values(row).forEach(visit);
  }
  visit(reason.evidence_json);
  return [...found.values()];
}
