# Phase 3 validation

Validated 6 October 2026 (IST). Repository: `ahirm-finarth/smarttrade`; branch `phase-3`, based on validated Phase 2 `85833484d02be0928e20a4dcac9bc56a4562d15d`. Phase 1/2 branches and main were not merged or changed.

The final delivery revision is the commit containing this report: `git log -1 --format=%H -- docs/PHASE3_VALIDATION.md`. A report cannot contain its own Git hash; the final response supplies the literal delivered HEAD and confirms the remote match. There are **13 focused Phase 3 commits**, including this report commit; the exact preceding hashes and final commit title are listed below.

## Delivered architecture and schema

Actual Phase 2 PDF-derived facts → current fact-role resolution → immutable input/rule snapshot → deterministic comparisons → relational evidence and supported findings. No model call, expected outcome or labelled reference enters runtime examination. See [architecture and full rule coverage](PHASE3_ARCHITECTURE.md).

Additive Alembic migration `4c4c93c90831` follows `e52fad8ad293`. Four tables added: `smart_trade_examination_runs`, `smart_trade_rule_executions`, `smart_trade_fact_relations`, `smart_trade_detected_discrepancies`. Indexed foreign keys and unique case/run, request identity, run/rule and execution/relation/finding constraints preserve ownership and prevent accidental duplicates. Phase 1 reference findings remain separate.

Ruleset `documentary-v1` has **41 unique versioned definitions**: Import LC 16, Export LC 14, Collection D/A 10, Performance Guarantee 9 applicable rules. Across the latest five cases: **65 executions**, 54 matches, 5 mismatches, 6 review results, **47 persisted two-fact relations**. Presence checks use real document-page proof but create no invented fact edge.

Ten comparison primitives: `NORMALIZED_TEXT`, `NORMALIZED_IDENTIFIER`, `PARTY_NAME_MATCH`, `PORT_MATCH`, `CURRENCY_EQUAL`, `AMOUNT_WITHIN_TOLERANCE`, `QUANTITY_EQUAL`, `DATE_ON_OR_BEFORE`, `CONTAINS_REQUIRED_TEXT`, `DOCUMENT_PRESENT`. Amounts use Decimal, explicit currency, configured tolerance/mode; no FX or inferred unit conversion. Conservative aliases never turn near party names into automatic matches.

## Actual source audit

All **18** registered original PDFs have current completed extraction runs. Their **111** current facts all pass source-quotation revalidation. The known clean-import packing-list own document reference is still missing: offline document-reference evaluation remains **17/18**. No replacement reference was hardcoded.

Source-only bounded extraction feedback recovered three bill-of-lading shipment dates, the export LC shipment deadline/exporter and the demand notice. Native printed labels guided omitted-field feedback; no ground-truth values were supplied. Supported fields from both bounded attempts are preserved, and contradictory supported values require review. Earlier processing and examination history remains intact.

Classification evaluation: 18/18 correct types; money 8/8, quantity/unit 8/8, goods 8/8 on their meaningful supplied labels. Dates still have no independent extraction accuracy denominator in the Phase 2 labels. Documentary deadline comparisons instead compare the actual two extracted dates.

The current guarantee demand classification confidence is **0.7200**, below the configured examination floor **0.85**. Current facts exist and are source-backed, but classification uncertainty prevents using that document as a trusted examination role. The threshold was not lowered to match labels.

## Latest results for all five cases

| Case | Status | Rules | Matched | Raw findings | Incomplete | Relations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ST-IMP-2026-0001 | CLEAN | 16 | 16 | 0 | 0 | 13 |
| ST-IMP-2026-0002 | DISCREPANCIES_FOUND | 16 | 13 | 3 | 0 | 13 |
| ST-EXP-2026-0003 | DISCREPANCIES_FOUND | 14 | 12 | 2 | 0 | 11 |
| ST-COL-2026-0004 | CLEAN | 10 | 10 | 0 | 0 | 8 |
| ST-BG-2026-0005 | INCOMPLETE_EXAMINATION | 9 | 3 | 0 | 6 | 2 |

Detected findings originate in the stored facts:

| Case / rule v1 | Expected | Observed | Evidence |
| --- | --- | --- | --- |
| Import risk · DOC-LC-AMOUNT-001 | USD 120,000.00 | USD 126,000.00 | LC and invoice, page 1 each |
| Import risk · DOC-LC-QTY-001 | 100 MT | 105 MT | LC and invoice, page 1 each |
| Import risk · DOC-IMP-PACK-QTY-001 | 100 MT | 105 MT | LC and packing list, page 1 each |
| Export · DOC-LC-SHIP-001 | Deadline 2026-03-15 | Shipment 2026-03-18 | Export LC and bill of lading, page 1 each |
| Export · DOC-EXP-PO-001 | PO-45078 | PO-45087 | Export LC and invoice, page 1 each |

Guarantee rules left for review: currency, amount cap, beneficiary, presentation/expiry, required breach statement and demand-document presence. Their classification uncertainty is explicit; no mismatch or clean conclusion was manufactured. Contract-party comparisons and contract presence match.

## Documentary evaluation

`make evaluate-demo-examination` reads the supplied reference discrepancy CSV only after persisted examinations. It emits machine-readable `reports/local/phase3-evaluation.json` and a human-readable `.md`; runtime never imports this evaluator. `make examine-demo-cases` independently selects operational DB cases and creates new examinations without reading labels.

| Measure | Actual |
| --- | ---: |
| Meaningful documentary reference families | 5 |
| Raw calculated findings | 5 |
| Detected case/finding families | 4 |
| True positives | 4 |
| False positives | 0 |
| False negatives | 1 |
| Precision | 1.0000 |
| Recall | 0.8000 |
| F1 | 0.8889 |
| Additional supported comparison for an already-matched label | 1 |
| Reference labels excluded as duplicate-financing risk | 1 |

The quantity label covers both LC/invoice and LC/packing quantity comparisons; both raw findings and IDs are published, while the labelled unit is case/finding family. Amount, quantity, date and PO values must match normalized reference values; type-only matching is tested and rejected. Required breach absence uses a controlled semantic family rather than claiming verbatim label-text accuracy.

**Known false negative:** DISC-0006, missing required breach statement, remains undetected because demand classification confidence is below threshold. This is counted as a miss. The explicit printed absence notice exists, but is not used to bypass classification confidence. Unit tests demonstrate the rule creates a finding when source-backed classification and statement-absence evidence are trustworthy. Null extraction alone creates no business finding.

**Known false positives:** none in the meaningful five-label evaluation. Duplicate invoice financing DISC-0003 is explicitly excluded as Phase 4 risk scope, not marked detected. Five synthetic cases do not establish production accuracy or exhaustive coverage.

## API and frontend

Eight endpoints added:

- POST `/api/v1/cases/{case_id}/examinations`
- GET `/api/v1/cases/{case_id}/examinations`
- GET `/api/v1/cases/{case_id}/examinations/latest`
- GET `/api/v1/examinations/{run_id}`
- GET `/api/v1/examinations/{run_id}/rule-executions`
- GET `/api/v1/examinations/{run_id}/findings`
- GET `/api/v1/cases/{case_id}/evidence-relations` (optional `run_id`)
- GET `/api/v1/cases/{case_id}/extracted-facts`

Case Examination tab: explicit run/rerun, history, documentary status/counters, calculated findings, filtered rule results, paired raw/normalized source facts with quotations, expandable relations and current extracted facts. Evidence links target the exact historical source version, extraction run and fact in the existing PDF viewer. Reference findings/risks remain clearly distinct from calculations and supplied expected outcomes.

A source image may fail before hydration attaches React's error handler. The final PDF workspace also checks the settled browser image state after hydration, enabling the existing preview error/Refresh recovery. The regression fixture holds its simulated image failure until explicit recovery.

Fresh Impeccable reviewer disposition: **ship**, all five contract sections returned, no material fixes. Detector ran once on the changed component: no findings. Fresh documenter preserved DESIGN.md and its token sidecar after checking desktop/mobile captures and the later functional hydration change. Ordinary extension; no new visual world or design-system rewrite. Existing system font/phase marker conventions remain unchanged.

## Executed verification

| Check | Result |
| --- | --- |
| Default backend suite | 108 passed; 4 opt-in MySQL checks skipped; no live LLM calls |
| Full suite with supplied MySQL | **112 passed** |
| Backend Ruff lint and format | Passed; 80 files formatted |
| Frontend desktop/mobile browser suite | **12 passed** |
| Frontend lint, typecheck, formatting | Passed |
| Frontend production build | Passed; dynamic dashboard, case and document routes |
| Additive MySQL migration | Upgrade head passed |
| Alembic model comparison | No new upgrade operations detected |
| Actual CLI examinations | All five stored runs completed, including honest incomplete guarantee result |
| Current source audit | 18 current PDFs; 111/111 source-verified facts |
| Offline extraction regression | 18/18 type, 17/18 reference, 8/8 money/quantity/goods |
| Secret scans | Passed before every commit/push; final history and frontend-build scan also passed |

Tests cover Decimal/currency/quantity/unit/date/text/party/identifier/required-text behavior, absent and low-confidence inputs, latest-version/latest-run selection, ambiguous roles, route derivation, relational provenance, immutable old evidence/rule versions, request UUID deduplication, active/expired workers, rollback on failure, failed latest extraction without old-fact fallback, no reference-file access at runtime, API ownership/error paths and actual MySQL persisted routes. All original Phase 1/2 tests remain included. Existing dependency deprecation warnings do not fail the suite.

Browser checks exercise actual API reruns, history immutability, both original source links, complete/incomplete states, current facts/relations, responsive containment and the existing document/overview/dashboard workflows. Only failure/stale-response scenarios are mocked; no live model request occurs in normal tests.

## Commit discipline and delivery

Every focused commit was scanned and pushed to `origin/phase-3`. No token-bearing remote, credentials, `.env`, originals in runtime storage, local reports, browser traces or generated frontend build are committed. Final local/remote HEAD equality and a clean working tree are checked after the report commit/push and recorded in the final response.

```text
7980f5e feat(evidence): add documentary examination and fact relation schema
615839f fix(ai): retry omitted fields using unique native PDF labels
33c5bc6 feat(examination): add deterministic trade fact comparison primitives
0e8641a feat(rules): add versioned documentary examination rule sets
7526733 fix(ai): preserve supported facts across bounded extraction retries
41d002f feat(evidence): resolve current cross-document fact roles safely
c8be0ea feat(examination): add cross-document documentary examination engine
310f3ca feat(api): expose documentary examination and evidence endpoints
e890a51 test(demo): add documentary examination regression evaluation
11f9d9f test(phase3): validate examination history and MySQL evidence workflows
58d11d8 fix(ui): target historical evidence and recover early PDF preview failures
0eaa338 feat(ui): add documentary examination and two-source evidence workspace
(this report commit) docs(phase3): document evidence graph and validation results
```

The final report commit's exact hash is obtained by the selector at the top; all other commits are listed literally. No application commit was made merely to create the branch.

## Deferred Phase 4 scope

Sanctions/PEP/adverse-media, vessel/country/port risk APIs, dual-use/restricted goods, fair-value checks, duplicate invoice/financing, facility/limit/credit checks; final PASS/REFER/BLOCK decisions and maker/checker actions; RAG, MiniLM/embeddings/vector database and regulatory retrieval; Smart Insights; SWIFT, core-trade integration and payments. No new container, cloud service or external graph database was introduced.
