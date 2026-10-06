# Phase 5: governed recommendations and human outcomes

Phase 5 extends the validated Phase 4 baseline (`4e5fa3a`) with additive MySQL persistence, deterministic decision policy, specialist routing, demo maker/checker actions, reviewed exceptions, optional advisory writing and a unified read-only audit. Source records, document versions, extracted facts, examination findings and risk findings remain separate and immutable. No payment, message submission or banking posting is performed.

## Persistence and source lineage

Migration `410e2781b143` follows `e32819e0cf3f`. Seven Smart Trade-owned tables use utf8mb4, foreign keys, indexes and uniqueness constraints:

| Table | Purpose |
| --- | --- |
| `smart_trade_decision_runs` | Case/run sequence, request identity, source examination/risk IDs, policy version, fingerprint, immutable input snapshot, recommendation and execution status |
| `smart_trade_decision_reasons` | Structured code, impact, severity, source status, queue, original finding/execution/check IDs and evidence JSON |
| `smart_trade_governed_workflows` | Separate mutable workflow projection, revision, maker/checker identities, final human outcome and timestamp |
| `smart_trade_workflow_tasks` | Role queue, claim, status, reason IDs and completion |
| `smart_trade_workflow_events` | Append-only controlled events, actor/role, rationale, request identity and structured metadata |
| `smart_trade_decision_overrides` | Appended supervisory exception acceptance, covered reasons, rationale, evidence reference and previous outcome |
| `smart_trade_finding_resolutions` | Appended specialist disposition and rationale; original findings are never rewritten |

A recommendation consumes an allowlisted operational case plus exact latest examination and risk DTO snapshots. Runtime code excludes expected outcomes, demo narratives and source status labels from its typed case input. Reference-label evaluation is isolated in `demo_decision_evaluation.py` after recommendations have been persisted.

The fingerprint includes source IDs, source fingerprints, findings, rule executions, provider checks, completeness and policy/routing snapshots. Currentness additionally checks latest document versions/runs and source policy/provider/reference versions. A newer decision supersedes older open tasks through cancellation events; it preserves their recommendation and evidence. A stale historical approval remains visible but its API `effective_final_outcome` is null and all actions are unavailable.

Generation serializes on the case row, uses request identity for retries, commits a RUNNING lease, and atomically persists completed outputs. Failure rolls back partial reasons/workflow/tasks and records a sanitized FAILED run. Abandoned decision leases expire after five minutes. Human commands lock the same case, require the current workflow revision and are idempotent for an identical request; reused identity with a different command conflicts.

## Deterministic decision policy

`decision-v1` is a compact typed configuration, not a generic rules DSL. BLOCK outranks REFER, which outranks PASS. Eleven structured reason codes cover the following condition families:

| Condition | Recommendation / reason |
| --- | --- |
| Missing examination or risk run | REFER / MISSING_SOURCE_RUN |
| Unavailable or failed source run | REFER / SOURCE_RUN_UNAVAILABLE |
| Stale source evidence or policy | REFER / STALE_SOURCE_RUN |
| Actual documentary mismatch | REFER / DOCUMENTARY_FINDING |
| Missing, unsupported, ambiguous or low-confidence comparison | REFER / INCOMPLETE_EXAMINATION |
| Missing configured mandatory category | REFER / MISSING_MANDATORY_CONTROL |
| Mandatory unchecked, insufficient, error or unknown provider result | REFER / MANDATORY_CONTROL_UNAVAILABLE |
| Candidate, potential, review or unconfirmed HIT / existing risk finding | REFER / RISK_REVIEW |
| Configured independently confirmed hard condition | BLOCK / CONFIRMED_HARD_BLOCK |
| Explicitly optional unchecked reference/financing control | INFO / OPTIONAL_CONTROL_UNCHECKED |
| All configured prerequisites complete with no unresolved referral/block | PASS / PASS_REQUIREMENTS_MET |

There are **11 reason codes**, including the PASS eligibility reason. Four categories are mandatory uniformly across the five synthetic playbooks: screening, port, vessel and local duplicate search. A justified NOT_APPLICABLE differs from NOT_CHECKED. Country, goods and fair-value references are explicitly optional; the independent financing-event control is also optional because no financing ledger exists. Their missing references remain unchecked and disclosed, including on PASS cases. This is a limited demonstration policy, not an assertion that those controls are optional in production.

Hard confirmation requires a provider HIT plus `confirmed=true`, a configured control identifier, an independent evidence ID and an explicit source. The configured controls are confirmed screening hit, prohibited condition and duplicate financing. Ordinary review candidates, provider errors and the absent ledger do not satisfy confirmation. None of the five supplied cases is artificially made BLOCK. An isolated test provider exercises confirmed BLOCK.

## Routing and workflow

`routing-v1` maps screening/country/port/vessel/goods to compliance; duplicate/fair-value to trade; documentary and incomplete comparisons to trade except Performance Guarantee to legal; hard BLOCK to supervisor. INFO reasons create no referral task. Task reasons sharing a queue are grouped. Credit/facility routing is deferred because no supported control exists in this dataset. Explicit escalation can create one of the bounded trade/compliance/legal/supervisor queues and records its target.

Roles: TRADE_MAKER, TRADE_CHECKER, TRADE_REVIEWER, TRADE_COMPLIANCE, LEGAL_REVIEWER, SUPERVISOR. Seven server-owned selectable demo identities map to these roles, including `dual.demo` holding maker/checker solely to demonstrate segregation. The selector is visibly fictional and provides no production authentication. Clients cannot supply a role or final outcome.

States: AWAITING_MAKER, AWAITING_CHECKER, AWAITING_SPECIALIST, REFERRED, NEEDS_INFORMATION, APPROVED, REJECTED, BLOCKED.

- PASS starts with maker review; maker submission creates a checker task. A distinct checker records final PASS.
- REFER starts with routed specialist review. A review-level RISK_REVIEW can be cleared with rationale; documentary mismatches cannot be cleared by a comment.
- Confirmed documentary issues can enter REFERRED and supervisory review. SUPERVISOR may accept eligible specialist-confirmed exceptions with selected reason IDs and rationale. The recommendation remains REFER; acceptance enables maker/checker eligibility without setting final PASS.
- Missing/incomplete mandatory evidence and stale inputs are unwaivable. Request information creates a maker information task and NEEDS_INFORMATION. Information-provided records a human response/reopens the requesting task, without inventing source evidence or clearing the original reason.
- Checker return creates new maker review. Any actor who submitted as maker at any point on the same decision remains forbidden from checking it, including after a return and another maker's submission.
- Rejection records separate human REJECT. A confirmed hard block can only be acknowledged as final BLOCK by its supervisor; no ordinary or supervisor override can produce PASS.
- Claimed tasks reject other identities even with the same role. Finalized/stale workflows reject further actions. Non-START actions require rationale; revisions reject concurrent stale edits.

## Optional Exception Resolution Agent

Explicit POST only; decision generation and ordinary workflow actions do not invoke the LLM. The agent receives existing reason evidence, bounded to 40 reasons/24,000 serialized characters, and the deterministic queues. It produces a short summary, grouped existing reason IDs, an advisory queue and reviewer/information-request drafts. JSON Schema and strict Pydantic validation reject extra authority fields, invented reason IDs, invalid queues and credential-shaped content. It uses the existing configured LLM client, 2,048 output tokens with at most one existing bounded truncation retry to 4,096. Configuration and private exceptions stay backend-only.

A validated output is saved only as EXCEPTION_SUMMARY_GENERATED audit input/output/prompt-version metadata. It changes no recommendation, finding, task, resolution, override, workflow revision or outcome. The v2 input also includes current governed state/outcome/revision, latest resolution codes, accepted exception IDs and unresolved reason IDs, with no human free-text rationale. Original OPEN statuses stay immutable and are explicitly distinguished from pending human work. The read transaction is released across model work; a fresh case lock/read checks currentness and the captured workflow revision after completion. An intervening human action discards the draft without undoing that action. Availability failure leaves deterministic governance usable. Natural-language drafts still require human verification; schema/ID validation does not prove every generated sentence true.

## API and frontend

Thirteen routes under `/api/v1`:

| Method | Path |
| --- | --- |
| GET | `/demo-actors` |
| POST, GET | `/cases/{case_id}/decisions` |
| GET | `/cases/{case_id}/decisions/latest` |
| GET | `/decisions/{id}` |
| GET | `/decisions/{id}/reasons` |
| GET | `/cases/{case_id}/tasks` |
| GET | `/tasks/{id}` |
| POST | `/tasks/{id}/actions` |
| POST | `/decisions/{id}/override` |
| POST | `/decisions/{id}/exception-summary` |
| GET | `/cases/{case_id}/audit` |
| GET | `/cases/{case_id}/workflow` |

403 denotes demo role/segregation failure; 409 denotes stale evidence, revision/request/transition conflicts; 422 denotes invalid commands; 503 denotes sanitized advisory unavailability. Read DTOs expose currentness, effective outcome, pending reasons and server-derived available actions.

Decision shows system/human outcomes side by side, history, policy, reasons, exact original quotations and source versions, and optional advisory drafts. Workflow supplies demo identity, inline rationale/action forms, task/resolution/override/event history and maker/checker constraints. Audit combines source processing, documentary examination, risk, decisions and governed events with exact historical source links. The original read-only Approvals tab remains reference history. Tables scroll inside the incumbent ledger on mobile; controls and statuses use its existing design tokens. No new raster assets ship.

## Deferred scope

No payment execution; SWIFT generation/submission; core trade/core banking posting; EDPMS/IDPMS; real sanctions/vessel/price providers; regulatory RAG or UCP/ISBP retrieval; MiniLM, embeddings or vector database; Smart Insights chatbot; post-event, guarantee expiry, export realization or import evidence monitoring; automated customer email. Production IAM/delegated financial authority, customer waivers, facility/credit controls, regulatory policy certification, OCR/vision, Docker, cloud storage and distributed workers remain later work.
