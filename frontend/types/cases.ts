export type Nullable = string | null;
export interface TradeCase {
  case_id: string;
  scenario: Nullable;
  product_playbook: Nullable;
  direction: Nullable;
  applicant: Nullable;
  beneficiary: Nullable;
  customer_id: Nullable;
  facility_id: Nullable;
  currency: Nullable;
  amount: Nullable;
  priority: Nullable;
  status: Nullable;
  expected_decision: Nullable;
  demo_narrative: Nullable;
  created_at: string;
  updated_at: string;
  is_synthetic: boolean;
}
export interface Party {
  id: number; party_role: Nullable; party_name: Nullable; country: Nullable; screening_status: Nullable;
}
export interface CaseDocument {
  id: number; document_id: Nullable; document_type: Nullable; reference: Nullable;
  expected: boolean | null; received: boolean | null; file_name: Nullable; extraction_confidence: Nullable;
}
export interface TradeLine {
  id: number; source: Nullable; item_no: number | null; goods_description: Nullable;
  quantity: Nullable; uom: Nullable; unit_price: Nullable; currency: Nullable; line_amount: Nullable;
}
export interface Discrepancy {
  id: number; finding_id: Nullable; severity: Nullable; rule_id: Nullable; category: Nullable;
  field: Nullable; expected_value: Nullable; observed_value: Nullable; evidence: Nullable;
  route_to: Nullable; status: Nullable;
}
export interface RiskEvent {
  id: number; risk_id: Nullable; risk_type: Nullable; subject: Nullable; provider: Nullable;
  result: Nullable; severity: Nullable; reason: Nullable;
}
export interface ApprovalEvent {
  id: number; event_time: Nullable; actor_role: Nullable; actor_id: Nullable; action: Nullable; outcome: Nullable;
}
export interface CaseDetail extends TradeCase {
  parties: Party[]; documents: CaseDocument[]; trade_lines: TradeLine[];
  discrepancies: Discrepancy[]; risk_events: RiskEvent[]; approvals: ApprovalEvent[];
}
export interface CaseList { items: TradeCase[]; total: number; limit: number; offset: number; }
export interface DashboardSummary {
  total_cases: number; synthetic_cases: number; expected_outcomes: Record<string, number>;
  product_distribution: { product: Nullable; count: number }[];
}
export interface CaseQuery { q?: string; product?: string; outcome?: string; limit?: number; offset?: number; }
