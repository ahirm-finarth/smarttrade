# Phase 4 validation

Validated 6 October 2026 (IST), repository `ahirm-finarth/smarttrade`, branch `phase-4`, based on Phase 3 `108649c0752f402c9f5b2194eb0c062810e261b6`. No merge into main or earlier phases. The final delivery revision is the commit containing this report: `git log -1 --format=%H -- docs/PHASE4_VALIDATION.md`. A report cannot embed its own Git hash; the final response gives the literal delivered hash and verified remote equality. There are **13 focused Phase 4 commits**, including this report commit. Application implementation HEAD before this documentation commit: `ec3908407a15037d5634dc69231016369699de6b`.

## Scope, schema and provider contracts

Operational parties and current source-derived facts → immutable risk input/provider/policy snapshots → provider checks → versioned risk rule executions → separate supported risk findings. No final transaction decision is calculated. [Architecture](PHASE4_ARCHITECTURE.md) documents configuration, source selection and lifecycle.

Additive Alembic revision **e32819e0cf3f**, following **4c4c93c90831**, adds four MySQL utf8mb4 tables:

1. `smart_trade_risk_runs`
2. `smart_trade_provider_checks`
3. `smart_trade_risk_rule_executions`
4. `smart_trade_detected_risk_findings`

Indexed foreign keys and case/run, case/request, run/check, run/check/rule and execution/subject uniqueness preserve ownership and prevent unintended duplication. Existing inventory/reference tables remain separate. Old completed risk runs retain original input/provider/rule/source snapshots. Active workers have a five-minute lease; UUID retries deduplicate uncertain submissions. Provider failure creates PARTIAL; persistence failure rolls outputs back and retains FAILED history.

Strict, credential-free `RiskProvider`, `ProviderInput`, `ProviderResult`, `ReferenceRecord` and `ProviderRegistry` contracts support seven replaceable categories. Synthetic implementations: party screening, country policy, port policy, vessel screening, goods policy and fair-value range checks. The seventh is deterministic local duplicate trade search. Typed `GoodsPolicy` and `PriceBand` constructors accept explicit reference configurations; defaults contain no invented policy or price band.

The four lookup providers use only `reference_screening.csv`. Its fictional `ZZ` is labelled reference metadata. No actual sanctions, geopolitical, vessel or legal classification claims are made. Country policy has no supplied row and therefore stays unchecked. Source identities are compared conservatively; near names are potential matches requiring review, never identity confirmation. Supplied party `screening_status`, expected decisions and risk-event/discrepancy labels do not enter runtime logic.

## Versioned rules and duplicate behavior

Ruleset **risk-v1**, eight version-1 rules, seven categories:

| Category | Rule | Configured severity |
| --- | --- | --- |
| Screening | RISK-SCREEN-001 | MEDIUM |
| Country | RISK-COUNTRY-001 | HIGH |
| Port | RISK-PORT-001 | HIGH |
| Vessel | RISK-VESSEL-001 | MEDIUM |
| Duplicate document | RISK-DUP-001 | MEDIUM |
| Independently evidenced financing | RISK-DUP-FINANCE-001 | HIGH |
| Goods | RISK-GOODS-001 | HIGH |
| Fair value | RISK-PRICE-001 | MEDIUM |

Only SIGNAL, DUPLICATE and FINANCING_EVENT handlers are supported. Invalid configurations fail validation; unknown handlers are refused. Provider failure/insufficient input statuses remain visible in rule audit.

Duplicate profiles batch-load actual current source invoices. Exact file SHA-256 yields EXACT_FILE_DUPLICATE (grade 1.00); complete commercial fingerprint yields DOCUMENT_DUPLICATE_CANDIDATE (0.97); invoice/seller/buyer/currency/amount, invoice/seller/buyer, or invoice/seller/currency/amount yield candidates with configured grades 0.95, 0.80 or 0.85. Grades are evidence ranks, not probabilities. Same case/document is excluded. Seller/amount alone is insufficient. Candidate case/document/version, matched/differing fields and both source chains are preserved.

The four actual current demo invoice profiles are distinct, so local search produces no candidate. The labelled historical invoice HIST-INV-OB-2025-889 is absent from storage; no fixture was invented. Reprocessing and source-version history are not financing events. The financing rule requires independent event ID/source and FINANCED status; no event ledger exists, so runtime financing remains NOT_CHECKED. A database-backed unit fixture proves cross-case matching and retirement of replaced current evidence without altering old finding snapshots.

Goods and fair value use trustworthy current goods, quantity, currency and source unit price or explicit total/quantity derivation. Decimal arithmetic, positive quantities and exact currency/unit matching are enforced. No FX, unit conversion, price band or legal mapping is inferred. Tests use explicitly synthetic configured bands/policies; these are not inserted into demo production inputs.

## Latest actual demo runs

Explicit CLI runs executed all five operational cases. Browser reruns created additional immutable risk history on the risk Import LC. Final audit after browser tests:

| Case | Run ID / number | Execution | Checks | Rule executions | Findings |
| --- | --- | --- | ---: | ---: | ---: |
| ST-IMP-2026-0001 | 13 / 2 | COMPLETED | 12 | 13 | 0 |
| ST-IMP-2026-0002 | 16 / 8 | COMPLETED | 12 | 13 | 3 |
| ST-EXP-2026-0003 | 12 / 2 | COMPLETED | 11 | 12 | 0 |
| ST-COL-2026-0004 | 11 / 2 | COMPLETED | 11 | 12 | 0 |
| ST-BG-2026-0005 | 10 / 2 | COMPLETED | 10 | 11 | 0 |

Totals: **56 provider checks, 61 rule executions, 3 risk findings**. Completed means execution finished, not clearance. Provider statuses: CLEAR 20, NOT_CHECKED 20, NOT_APPLICABLE 13, POTENTIAL_MATCH 1, NEEDS_REVIEW 2. Actual latest demo runs have zero PROVIDER_ERROR and zero INSUFFICIENT_DATA checks. Financing's separate rule remains unchecked for every current invoice despite local duplicate search clear results.

All three supported findings are on ST-IMP-2026-0002:

| Finding / rule v1 | Severity | Original source | Independent mock reference |
| --- | --- | --- | --- |
| Vesper Commodities FZE / RISK-SCREEN-001 | MEDIUM | LC beneficiary fact 150 and invoice seller fact 157, page 1 | DEMO-SCR-003 |
| Port Azure / RISK-PORT-001 | HIGH | BL discharge-port fact 189, page 1 | DEMO-SCR-001 |
| MV Meridian Halo / RISK-VESSEL-001 | MEDIUM | BL vessel fact 186, page 1 | DEMO-SCR-002 |

All cited facts have confidence 0.9800 and revalidated source quotes. Vessel/port use document 8, version 15, extraction run 45. Party citations use document 5/version 17/run 39 and document 6/version 16/run 40. Provider reference ID/name/note, version, policy ID/version and severity are retained in each finding. Categories: screening 1, port 1, vessel 1; country/duplicate/goods/fair-value 0. No calculated approval or PASS/REFER/BLOCK action exists.

## Independent risk evaluation

`make evaluate-demo-risk` separately reads labels after persisted checks; runtime never imports the evaluator. Ignored machine/human outputs: `reports/local/phase4-risk-evaluation.json` and `.md`. `make run-demo-risk` selects only operational DB cases and does not read labels.

The primary denominator includes all five in-scope positive labels: route, vessel, independent mock counterparty reference joined to actual party, fair value and duplicate. Match units are case/category/normalized subject, with duplicate case/category matching because the supplied label has no stored candidate tuple. Wrong subject matches are tested and rejected. Raw finding IDs and per-category scores are published.

| Measure | Actual |
| --- | ---: |
| Expected in-scope positives | 5 |
| Raw detected signals | 3 |
| True positives | 3 |
| False positives | 0 |
| False negatives | 2 |
| Precision | 1.0000 |
| Recall | 0.6000 |
| F1 | 0.7500 |
| Clean Import LC false material findings | 0 |

**Misses retained in the primary metric:** RISK-0004 fair-value review has no supplied reference price band; DISC-0003 duplicate invoice has no stored historical candidate or independent financing event. Missing inputs are not excluded to inflate recall. Country/goods have no independent positive ground-truth denominator, so their category accuracy is unscored; numeric zero-denominator values in JSON are placeholders, not accuracy claims.

**Out-of-scope reference events:** RISK-0005 export realisation watch is deferred post-event monitoring; RISK-0006 guarantee condition breach belongs to Phase 3 documentary examination and is not duplicated as a risk signal. Two exclusions are explicit, not counted as detected. Five fictional cases are not a production benchmark.

## API and frontend

Eight additive endpoints under `/api/v1`:

- POST `/cases/{case_id}/risk-runs`
- GET `/cases/{case_id}/risk-runs`
- GET `/cases/{case_id}/risk-runs/latest`
- GET `/risk-runs/{run_id}`
- GET `/risk-runs/{run_id}/provider-checks`
- GET `/risk-runs/{run_id}/rule-executions`
- GET `/risk-runs/{run_id}/findings`
- GET `/cases/{case_id}/duplicate-candidates`

Runs accept optional request UUID; invalid extra decision input is rejected. Detail includes current-input flag. Unknown case/run returns 404, invalid payload 422, active worker 409, database unavailable sanitized 503. Candidate GET does not create examination or risk history.

Risk & Compliance workspace adds explicit run/rerun and refresh, history, execution status/counts, seven-category ledger, findings, filtered provider checks, source/provider/policy evidence pair and full rule audit. Exact historical source links open the existing PDF fact viewer. Missing references, stale inputs, partial providers and request recovery are explicit. Supplied reference risks and documentary results remain separate.

Fresh Impeccable documenter checked the source and all six captures, preserved DESIGN.md and its token sidecar, and reported existing Phase 3 token/wording drift without repairing it. Fresh Impeccable full reviewer returned all five contract sections, with one material fix: reveal the selected risk tab in the mobile strip. One correction adjusts only horizontal strip scroll; final desktop/mobile tests verify full selected-tab visibility and unchanged vertical position. Same six captures were repeated, and reviewer verdict **ship** scored the requested fix resolved. Detector ran once with no findings. Ordinary extension preserves the incumbent design system; no new world, comp or shipping raster.

## Executed validation and regression

| Check | Result |
| --- | --- |
| Baseline full Phase 3 suite before changes | 112 passed |
| Default final backend suite | **158 passed, 5 opt-in MySQL tests skipped** |
| Full final suite with supplied MySQL | **163 passed** |
| Backend Ruff lint / formatting | Passed, 102 files formatted |
| Final browser suite | **18 passed**, 9 desktop + 9 mobile |
| Frontend lint / typecheck / formatting | Passed |
| Final production build | Passed, Next.js 16.3.8 Webpack |
| MySQL additive upgrade head | Passed |
| Alembic model comparison | No new upgrade operations detected |
| Final risk CLI | Five actual runs completed, no LLM calls |
| Original documentary history audit | All **20** original examination rows unchanged |
| Current source audit | **18** current original PDFs, **111/111** source-verified facts |
| Extraction regression | Type 18/18, reference 17/18, money/quantity/goods 8/8 each |
| Secret scans | Passed before every focused commit/push; history + frontend build passed |

Risk tests cover strict contracts/secret rejection, exact/conservative synthetic matching, absent references, optional subjects, Decimal price policies, cross-case duplicates/current-version retirement, file vs financing distinction, immutable old audit, UUID retries, active/expired leases, provider failure, missing reference availability, rollback and full API/MySQL audit. Browser checks exercise real API reruns, three actual signals, source/provider/policy evidence, historical source navigation, saved history, clean unchecked price and mobile selected tab. Only failure/stale scenarios are mocked; no live model call is made.

All Phase 1–3 tests remain included. The shared fact resolver's builder extraction preserves its existing behavior. The original 20 Phase 3 fingerprints/statuses/summaries match the pre-change baseline exactly. Current documentary results remain clean Import, three risk Import discrepancies, two Export discrepancies, clean Collection and six Guarantee review results. Demand classification remains 0.72 below 0.85; the packing-list own reference remains a known extraction miss. No confidence lowering, ground-truth replay or source reprocessing was performed in Phase 4.

## Commit discipline and final delivery

All focused commits were scanned and pushed only to `origin/phase-4`. No credential-bearing remote, environment files, runtime originals, evaluation reports, screenshots, traces, caches or compiled build files are committed. Final local/remote equality and clean working tree are verified after this report commit; literal final hash is supplied in the final response. Earlier branch tips remain Phase 1 `53c6246c363bf3c921d42d998576f1e7a5b7f4c8`, Phase 2 `85833484d02be0928e20a4dcac9bc56a4562d15d`, Phase 3 `108649c0752f402c9f5b2194eb0c062810e261b6`.

```text
000a026ad3c54680a4580638c95e013e82499932 feat(risk): add auditable risk orchestration persistence
8757d754dc64def79de8edef320d494a15412835 feat(risk): add pluggable trade risk provider contracts
9237a7d450672c0fcb16967dd814661370470c99 feat(screening): add synthetic party and route risk providers
880037d1ad334411649596d03d98144d4701f443 feat(risk): add explainable duplicate trade detection
7c13383fffde77b8fd36bc69c5482ba2e7b7981f feat(risk): add synthetic goods and fair-value controls
850756838d7ea929f92ec5ba98fa26db24555d1f feat(rules): add versioned trade risk and compliance controls
fb6f99a991a40a7922d8cd255ee4ba3012da9e41 feat(risk): orchestrate auditable case-level risk checks
b2e217524497efc2e15c3a5dc2991e8a315e70bf feat(api): expose Smart Trade risk and compliance workflows
f505cd9c05cdc6468a40753a95b3076f1314cc63 feat(evaluation): measure synthetic risk findings independently
b3f7c04fa0896ceec7b52a1cbd9229069157d87a fix(risk): audit unavailable references and preserve failure states
02a87187b013e6e25e7130a3444aa6051ca69de5 test(risk): verify persisted MySQL provider audit workflows
ec3908407a15037d5634dc69231016369699de6b feat(ui): add auditable risk and compliance workspace
(this report commit) docs(phase4): document risk architecture and validation results
```

The exact report commit hash is obtained by the selector at the top. No empty branch-creation or deployment commit was added.

## Exact deferred Phase 5 or later scope

Final PASS / REFER / BLOCK transaction decisioning; combined documentary + risk decision matrix; human maker/checker actions; overrides; delegated authority; approval matrix; payment release; SWIFT generation/posting; core trade posting; EDPMS/IDPMS integration; real sanctions vendors; real vessel vendors; real fair-value APIs; regulatory RAG; UCP/ISBP retrieval; MiniLM; embeddings; vector database; Smart Insights chatbot; post-event monitoring. No Docker/cloud/queue/Celery/Redis infrastructure was added. Facility/credit controls and an independently sourced financing-event ledger are also absent from this synthetic Phase 4 implementation.
