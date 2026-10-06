# Phase 5 validation: governed decisions and approvals

Branch: **phase-5** in `ahirm-finarth/smarttrade`. Base: validated Phase 4 `4e5fa3a0ecf02c668d596168653c2038d306c1ca`. Delivery has **13 focused commits**, including this report commit. Implementation revision: `8cf8e23047d92fc9a0fb30c515fc29c68edc2841`.

The final delivery revision is the commit containing this report, selected exactly by `git log -1 --format=%H -- docs/PHASE5_VALIDATION.md`. A commit cannot embed its own Git hash; the literal final hash is supplied in the delivery response. Final local/remote equality and a clean working tree are checked after pushing the report.

## Schema and deterministic policy

Migration **410e2781b143**, following `e32819e0cf3f`, adds seven utf8mb4 tables with foreign keys, indexes and uniqueness constraints:

- `smart_trade_decision_runs`
- `smart_trade_decision_reasons`
- `smart_trade_governed_workflows`
- `smart_trade_workflow_tasks`
- `smart_trade_workflow_events`
- `smart_trade_decision_overrides`
- `smart_trade_finding_resolutions`

The immutable recommendation/snapshot is separate from the mutable governed workflow projection and appended human events, resolutions and exception acceptances. Generation uses case-row locking, request UUIDs, five-minute worker leases, atomic output persistence and sanitized failure records. Tests confirm failures leave no partial reasons, tasks or workflow.

`decision-v1` has **11 structured reason codes**. BLOCK outranks REFER, which outranks PASS. Expected labels are excluded from runtime case inputs and read only by independent offline evaluation after decisions are persisted.

| Code | Condition / effect |
| --- | --- |
| MISSING_SOURCE_RUN | Missing examination/risk run → REFER |
| SOURCE_RUN_UNAVAILABLE | Unavailable/failed source run → REFER |
| STALE_SOURCE_RUN | Stale evidence or policy → REFER |
| DOCUMENTARY_FINDING | Actual documentary mismatch → REFER |
| INCOMPLETE_EXAMINATION | Missing, unsupported, ambiguous or low-confidence comparison → REFER |
| MISSING_MANDATORY_CONTROL | Missing mandatory category → REFER |
| MANDATORY_CONTROL_UNAVAILABLE | Mandatory unchecked/insufficient/error/unknown check → REFER |
| RISK_REVIEW | Potential, review or unconfirmed HIT / risk finding → REFER |
| CONFIRMED_HARD_BLOCK | Configured independent confirmation → BLOCK |
| OPTIONAL_CONTROL_UNCHECKED | Explicit optional unchecked control → informational disclosure |
| PASS_REQUIREMENTS_MET | Configured prerequisites complete with no unresolved referral/block → PASS |

The same limited demo policy requires screening, port, vessel and local duplicate controls for all five playbooks. Country, goods and fair-value references and the absent independent financing ledger are explicitly optional and disclosed. NOT_CHECKED is never presented as NOT_APPLICABLE or a successful check. This policy does not establish production regulatory sufficiency or live clearance.

Hard BLOCK requires a provider HIT, explicit confirmation, a configured hard-control identifier, an independent evidence ID and its source. Confirmed screening, prohibited condition and duplicate financing are configured. Candidate matches and unavailable controls cannot manufacture confirmation. None of the five reference cases is artificially converted to BLOCK.

## Routing, roles and human controls

`routing-v1` sends screening/country/port/vessel/goods to compliance; duplicate/fair-value to trade; documentary/incomplete results to trade except Performance Guarantee to legal; confirmed BLOCK to supervisor. INFO reasons create no referral task. Supported escalation queues are bounded to trade/compliance/legal/supervisor. Facility/credit routing is deferred because supported facility evidence is absent.

Eight states: **AWAITING_MAKER, AWAITING_CHECKER, AWAITING_SPECIALIST, REFERRED, NEEDS_INFORMATION, APPROVED, REJECTED, BLOCKED**.

Six roles: **TRADE_MAKER, TRADE_CHECKER, TRADE_REVIEWER, TRADE_COMPLIANCE, LEGAL_REVIEWER, SUPERVISOR**. Seven server-owned demo identities include a dual maker/checker actor for segregation testing. The selector is explicitly demo identity, not production authentication; client role and final-outcome fields are rejected.

Twelve bounded actions: START, SUBMIT_FOR_CHECKER, APPROVE, RETURN_TO_MAKER, REFER, REJECT, CONFIRM_CLEAR, CONFIRM_ISSUE, REQUEST_INFORMATION, INFORMATION_PROVIDED, ESCALATE, ACKNOWLEDGE_BLOCK. Backend authority checks, task claims, required rationales, current revisions and idempotent request identities govern commands.

Maker submission creates checker review. Any actor who submitted as maker at any point on that decision cannot check it, even after a checker return and another maker's submission. Only a distinct checker can produce final human PASS after prerequisites are complete. REJECT is a separate human outcome; original recommendations remain immutable.

A SUPERVISOR can accept selected, current, specialist-confirmed DOCUMENTARY_FINDING/RISK_REVIEW exceptions with rationale. This only restores maker/checker eligibility; it does not itself approve or rewrite findings. Incomplete comparisons, missing mandatory evidence, stale decisions and hard BLOCK cannot be waived. Documentary mismatches cannot be cleared with a comment. BLOCK can be acknowledged only as final BLOCK, never PASS.

Information-provided records a response and reopens review; it does not invent evidence or clear the underlying gap. A newer source run/document/policy or decision invalidates authority on the older decision. Historical human PASS remains visible, but `effective_final_outcome` becomes null and actions are unavailable.

## Actual five-case demo results

These are actual persisted local MySQL workflows from `run_demo_workflows`, inspected separately through API/browser. They are explicitly synthetic training actions, not real customer waivers, live provider clearance or execution authority.

| Case | Decision ID | Examination / risk IDs | System recommendation | Final governed state / outcome |
| --- | --- | --- | --- | --- |
| Clean Import LC ST-IMP-2026-0001 | 49 | 14 / 13 | PASS | APPROVED / PASS after distinct maker/checker |
| Risk Import LC ST-IMP-2026-0002 | 50 | 28 / 18 | REFER | APPROVED / PASS after compliance review, three confirmed documentary issues, supervisor acceptance, maker/checker |
| Export LC ST-EXP-2026-0003 | 48 | 13 / 12 | REFER | APPROVED / PASS after two confirmed documentary issues, supervisor acceptance, maker/checker |
| Collection ST-COL-2026-0004 | 47 | 12 / 11 | PASS | APPROVED / PASS after distinct maker/checker |
| Guarantee ST-BG-2026-0005 | 46 | 10 / 10 | REFER | NEEDS_INFORMATION / no final outcome; legal review and open information request |

Risk Import resolutions 35–40 and supervisor acceptance 8 are appended records. Export resolutions 33–34 and acceptance 7 are appended records. Original three Import discrepancies, two Export discrepancies and risk findings remain intact. Both system recommendations remain REFER after final human PASS.

Guarantee has six incomplete comparisons. Its original demand classification confidence remains 0.72 below the established 0.85 threshold; no classification threshold was lowered and no guarantee breach was invented. Completing that case requires better source-supported evidence and new source examination/decision, not a waiver of incompleteness.

Local ignored reports: `reports/local/phase5-workflows.json`, `phase5-decision-evaluation.json`, `phase5-live-inspection.json`, `phase5-preservation.json`, `phase5-advisory-payload-proof.json` and optional `phase5-advisory.json`. Runtime evidence, screenshots and reports are deliberately excluded from Git.

## Offline evaluation and workflow scenarios

Actual persisted recommendation accuracy is **5/5 = 100%**. PASS: support 2, precision/recall 1.0; REFER: support 3, precision/recall 1.0. BLOCK has support 0; its precision/recall are undefined, not a claimed 100%. Evaluation tests verify real misses change metrics and missing predictions are misses. Five synthetic examples do not establish production accuracy.

| Scenario | Executed result |
| --- | --- |
| Clean PASS | Maker → distinct checker → final PASS; audit appended |
| REFER documentary/risk workflow | Routed specialist review → bounded supervisor acceptance → maker/checker → human PASS while system REFER remains |
| Guarantee incomplete examination | Legal review → REQUEST_INFORMATION → NEEDS_INFORMATION; no final PASS |
| Dual-role maker checks own submission | Backend 403; rejected without authority mutation |
| Checker returns; another maker submits | Earlier maker still forbidden from checking same decision |
| Wrong role, claim, transition, revision or conflicting request reuse | Rejected; no unauthorized mutation |
| Unreviewed/unauthorized supervisory exception | Rejected |
| Missing/incomplete evidence after confirmed issue | Cannot clear or waive; no final outcome |
| Confirmed hard BLOCK fixture | Deterministic BLOCK; ordinary and supervisor PASS overrides rejected |
| Hard BLOCK acknowledgment | Supervisor-only final BLOCK; never PASS |
| New upstream risk run after approval | Prior PASS becomes historical and ineffective, snapshot unchanged |
| New document version before source rerun | Old decision immediately stale; no approval authority |
| Stale API command | 409; original evidence/outcome history preserved |
| Failed generation persistence | FAILED record with sanitized error and no partial output |
| Advisory unavailable or structurally unsafe | Safe failure; deterministic decisions and workflow remain usable |
| Resolved governance with original OPEN findings | Separate immutable statuses from final PASS, reviewed exceptions and empty pending IDs |
| Workflow action during advisory generation | Output rejected, no advisory event saved; committed maker action preserved |

Hard BLOCK is an isolated test provider with independent confirmation, not a relabelled production case. Browser tests use real API generation/workflows for normal scenarios; only failure/advisory/stale availability scenarios are mocked.

## Optional Exception Resolution Agent

The explicitly invoked agent summarizes existing reasons/evidence, groups existing IDs, suggests an allowed deterministic queue and drafts reviewer/information-request notes. It receives at most 40 reasons / 24,000 serialized characters, uses 2,048 output tokens with at most one bounded 4,096-token truncation retry, and validates strict JSON/Pydantic contracts. Unknown reason IDs, authority fields, unsupported queues and credential-shaped content are rejected. No ordinary decision/workflow operation calls it automatically.

Validated output is advisory and appended to audit. It cannot change recommendation, source findings, severity, routing, tasks, resolutions, overrides, workflow revision or final outcome. Currentness is checked again after model completion. Natural-language drafts require human source verification; schema validation cannot prove every sentence correct.

Mocked advisory success, unsafe output rejection, idempotency and unavailable-provider recovery passed. A first live check was rejected by automatic approval review because the payload authorization was unclear. Before retrying the same command, the actual 12-reason / 16,423-byte original payload (16,747 bytes with v2 governance context) was checked: demo-only flag, credential guard, every source document SHA256 matching publicly committed fictional watermarked demo PDFs, and explicit configured-LLM authorization in the supplied Phase 5 request (lines 1153–1183). The endpoint/key remain private and backend-only. The first valid v1 draft described source OPEN findings without later human resolutions. This prompted a bounded v2 correction: governance state/outcome/revision, latest resolution codes, accepted reason IDs and unresolved reason IDs accompany immutable source statuses; human free-text rationale is excluded. The model prompt distinguishes original findings from pending human issues and avoids asking for completed reviews again. A workflow-revision check rejects drafts when a human action intervenes; the pre-model transaction is released and the case is locked before a fresh post-model read, avoiding an old MySQL repeatable-read snapshot.

The live v1 check returned a validated advisory event **350** for decision **50**, and an exact before/after tuple verified unchanged recommendation, workflow state/outcome/revision, tasks, resolutions and overrides. Its source values, finding IDs and deterministic queue matched the saved synthetic evidence, but its prose lacked later human resolution context. The final v2 live attempt returned **UNAVAILABLE** with private diagnostics suppressed; no v2 output was saved. Final v2 context and workflow-race protection passed all seven focused advisory tests. Therefore live end-to-end validation is established for the original bounded client path, while a valid live v2 draft remains unverified. Provider/model output failure is an explicit optional-feature limitation; deterministic governance remains usable. Historical v1 audit evidence is preserved, not rewritten.

## API and frontend

Thirteen new method/path combinations under `/api/v1`:

| Method | Path |
| --- | --- |
| GET | /demo-actors |
| POST | /cases/{case_id}/decisions |
| GET | /cases/{case_id}/decisions |
| GET | /cases/{case_id}/decisions/latest |
| GET | /decisions/{id} |
| GET | /decisions/{id}/reasons |
| GET | /cases/{case_id}/tasks |
| GET | /tasks/{id} |
| POST | /tasks/{id}/actions |
| POST | /decisions/{id}/override |
| POST | /decisions/{id}/exception-summary |
| GET | /cases/{case_id}/audit |
| GET | /cases/{case_id}/workflow |

403 rejects role/segregation violations; 409 rejects stale/concurrent/transition conflicts; 422 rejects invalid commands; advisory unavailability returns sanitized 503. The read-only audit assembles original processing/examination/risk history with decision/governance events, preserving exact historical source links without copying source events into a duplicate store.

Three new frontend views: **Smart Trade Decision**, **Governed Approvals & Workflow**, **Case Audit**. They expose separate system/human outcomes, immutable reason evidence, run history, exact source versions, explicit demo actors, inline rationale/action forms, specialist resolutions, supervisory acceptance and chronological audit. Existing reference Approvals remains read-only. Same-case source navigation remounts the selected historical workspace correctly. Retry identity is retained for uncertain identical commands, and old-role availability cannot flash usable controls during actor changes.

Impeccable was used for the incumbent Operate extension. Parent inspected one desktop/mobile batch and one confirmation; detector ran once with no findings. The first fresh reviewer failed at its usage limit and was replaced once. The replacement full reviewer identified two material fixes: new buttons' 44px minimum and task heading preceding revision text. Both were corrected in one batch, rebuilt and recaptured over all 12 valid full/top screenshots. The same reviewer scored **both fixes resolved**, disposition **ship at the two-fix verdict scope**. This is not a claim of a second whole-surface review. No new fonts, comp, visual world or shipping raster were introduced.

A fresh Impeccable documenter checked all 12 final screenshots, the incumbent Phase 4 calibration, component source and tokens. DESIGN.md and .impeccable/design.json hashes remained unchanged; the direction brief records the finish evidence. Inherited system-font display/phase-marker craft exceptions and reference-focused palette wording were reported without repairing or broadening the incumbent system. Review and documentation are complete.

## Executed validation and Phase 1–4 regression

| Check | Result |
| --- | --- |
| Phase 4 baseline backend before changes | **163 passed**, supplied MySQL |
| Full final backend suite | **224 passed**, including six MySQL integration tests; 127.53s |
| Default backend suite before final advisory correction | 216 passed before the two additional advisory-context tests, six opt-in MySQL tests skipped; final full run includes all 224 tests |
| Focused Phase 5 browser suite | **8 passed**, four scenarios on desktop/mobile |
| Full browser regression | **26 passed**, 13 desktop + 13 mobile; 5.5min |
| Ruff lint / formatting | Passed; 132 files formatted |
| ESLint / Prettier | Passed |
| TypeScript / generated route types | Passed |
| Next.js 16.3.8 production Webpack build | Passed, including review-fix rebuild |
| Final review recapture assertions | All new buttons 44px; no body overflow across six device/view combinations |
| MySQL migration | Head **410e2781b143**, additive upgrade applied |
| Alembic schema/model comparison | No new upgrade operations detected |
| Original upstream preservation | **1,577 / 1,577** original rows unchanged across 21 tables |
| Current fact source verification | **111 / 111** source-verified |
| Original PDF/version and extraction history | 18 versions and 50 processing runs unchanged |
| Offline decision evaluation | **5 / 5** actual recommendations matched |
| Secrets | Tracked files + all Git history + frontend build scans passed before each commit/push |

The full suites include the existing Phase 1–4 tests. Final UI changes only adjust new button minimum height and task-heading order; the rebuilt captures confirm those fixes. Six dependency deprecation warnings occurred in the backend run, with no failing tests.

Original-row hashes compare every pre-change row, not just aggregate counts. All supplied reference tables, cases, parties, trade lines, approvals, documents, facts, old examination/risk runs, discrepancies, provider checks and evidence relations match. Browser regression appended two examination and two risk runs; no original record changed. Preservation counts below show both the immutable originals and final table totals.

| Upstream table (smart_trade_ prefix) | Original / final rows | Changed original rows |
| --- | --- | --- |
| cases | 5 / 5 | 0 |
| demo_risk_rules | 14 / 14 | 0 |
| demo_screening_references | 3 / 3 | 0 |
| approval_events | 7 / 7 | 0 |
| case_documents | 18 / 18 | 0 |
| case_parties | 12 / 12 | 0 |
| discrepancies | 6 / 6 | 0 |
| examination_runs | 26 / 28 | 0 |
| risk_events | 6 / 6 | 0 |
| risk_runs | 16 / 18 | 0 |
| trade_lines | 9 / 9 | 0 |
| document_versions | 18 / 18 | 0 |
| provider_checks | 184 / 208 | 0 |
| document_pages | 18 / 18 | 0 |
| document_processing_runs | 50 / 50 | 0 |
| risk_rule_executions | 200 / 226 | 0 |
| detected_risk_findings | 24 / 30 | 0 |
| extracted_facts | 215 / 215 | 0 |
| rule_executions | 386 / 418 | 0 |
| detected_discrepancies | 58 / 64 | 0 |
| fact_relations | 302 / 328 | 0 |

## Commit discipline and delivery

Every focused commit is scanned and pushed only to `origin/phase-5`. No GH_TOKEN, LLM_API_KEY, MySQL password, credential-bearing remote, `.env`, runtime source storage, local reports, screenshots, caches or builds are committed. No force push, merge, deployment or earlier branch update is performed. Final local/remote equality and clean-tree checks follow the report commit.

Earlier phase tips remain unchanged:

```text
phase-1 53c6246c363bf3c921d42d998576f1e7a5b7f4c8
phase-2 85833484d02be0928e20a4dcac9bc56a4562d15d
phase-3 108649c0752f402c9f5b2194eb0c062810e261b6
phase-4 4e5fa3a0ecf02c668d596168653c2038d306c1ca
```

Exact focused commits, oldest first:

```text
ccfeccc802adfd2a90fd4761372310b7bdd4769d feat(decision): add governed decision and workflow persistence
ee7457edc7cbfcc37bee7c18ffba2be5cab72286 feat(decision): add deterministic trade decision matrix
eeec3a87fa1aa80de3a9926ea667ebf0e18f2113 feat(workflow): route decision exceptions to specialist queues
a78161ef5d5bcc364e51e61576856210d636e05b feat(decision): persist source snapshots and routed exception tasks
0f79c335bbac110f4d0107197c70ea1fa726afd3 feat(workflow): add governed maker checker and specialist actions
79ef5a716a269694fc4fe2d670d5fdc991a1a151 feat(controls): add auditable reviewed exception overrides
80c9110c9305cbe07daa64ba8408988e6ca355e6 feat(ai): add bounded advisory exception resolution summaries
56737bc34da8b752bb2a0a33db713c019ce43dca feat(api): expose governed decisions approvals and case audit
7eee52db36a9e0741922ed89c1bd3ebc3f9e032d feat(ui): add governed decision workflow and audit workspaces
e8cd99c9d4ce9d6a8ed670286d51b188a0a10fa1 fix(ui): align governed controls and task hierarchy
f07c2812a7fec93ea8e03bdd00a0240b5e1482fe test(decision): verify governed workflows and demo evaluation
8cf8e23047d92fc9a0fb30c515fc29c68edc2841 fix(ai): preserve governed context during advisory drafting
(this report commit) docs(phase5): record governed decision architecture and validation
```

The exact report commit uses the selector at the top; no empty branch-creation commit was added. Reproduction commands are documented in README.md and Makefile; architecture and control boundaries are in PHASE5_ARCHITECTURE.md.

## Exact Phase 6 or later deferred scope and limitations

Deferred: payment execution; SWIFT message generation/submission; core trade posting; core banking posting; EDPMS integration; IDPMS integration; real sanctions providers; real vessel providers; real price providers; regulatory RAG; UCP/ISBP retrieval; MiniLM; embeddings; vector database; Smart Insights chatbot; post-event monitoring; guarantee expiry monitoring; export realization monitoring; import evidence monitoring; automated customer email.

Also unresolved: production IAM and delegated financial authority, actual customer waivers, certified production/regulatory policy, facility/credit controls, independently sourced financing events, OCR/vision and the original known packing-list reference extraction miss. Country/goods/price and independent financing coverage remain explicitly unchecked optional demo controls. Guarantee remains incomplete. Synthetic 5/5 accuracy and synthetic supervisory acceptance cannot be interpreted as real transaction authorization. Docker, cloud storage, distributed queues, Celery and Redis were not added.
