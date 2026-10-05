# Documentary examination and relational evidence

Phase 3 extends Phase 2 PDF-derived facts with deterministic cross-document examination. It produces documentary findings and incomplete comparisons, never a final PASS/REFER/BLOCK decision. No model call, reference dataset or regulatory inference participates in examination.

## Data flow

1. Resolve the operational case playbook.
2. Select each document's latest immutable version and latest extraction run. Do not fall back to an older successful run. Actual classified document types define roles; multiple current candidates require review.
3. Batch-load source pages/facts and revalidate each quotation against the native page. Apply the configured classification/fact confidence floor, default `0.85`.
4. Snapshot the current evidence, full typed rules and effective threshold; fingerprint that snapshot.
5. Execute the applicable deterministic comparisons and persist every result.
6. Link both real fact IDs when available; create a detected finding only for a supported two-sided mismatch. Missing, unsupported, ambiguous, low-confidence and non-comparable inputs remain incomplete.
7. Retain immutable history. A rerun uses new current inputs and a new run ID. A repeated request UUID returns the same submission.

The engine imports neither CSV/XLSX/JSON reference readers nor the offline evaluator. `examine_demo_cases` operates only on operational database cases; `evaluate_demo_examination` reads labels after stored examination.

## Additive MySQL schema

Revision `4c4c93c90831` follows Phase 2 revision `e52fad8ad293` and adds four Smart Trade tables:

| Table | Purpose |
| --- | --- |
| `smart_trade_examination_runs` | Case/run/request identity, ruleset, status, UTC times, fingerprint, immutable input snapshot and summary |
| `smart_trade_rule_executions` | Unique rule per run, rule version/full config, two resolved inputs, result/reason/details |
| `smart_trade_fact_relations` | Source/target fact foreign keys, examination/execution provenance, relation type/result/confidence |
| `smart_trade_detected_discrepancies` | Supported calculated finding, severity, rule/version, immutable expected/observed evidence |

Foreign keys and lookup indexes connect case, run, execution and facts. Case/run and case/request UUID uniqueness prevent accidental duplicates; each execution has at most one relation and finding. Phase 1 `smart_trade_discrepancies` remains a separate reference inventory.

Relations are `GOVERNS`, `COMPARED_WITH` or `SUPPORTS`. A document-presence check uses actual classified/readable source-page evidence without inventing an extracted fact ID, so it creates no two-fact edge. Missing inputs also create no edge.

## Comparison policy

Ten primitives are implemented: normalized text, normalized identifier, party name match, port match, currency equality, amount within tolerance, quantity equality, date on/before, required text and document presence.

Money uses finite Decimal strings, explicit currency and an explicit rule tolerance/mode. No FX conversion. Quantity comparison uses controlled piece/set aliases; different units remain non-comparable. Identifiers preserve meaningful token boundaries and zeros. Party normalization uses a narrow corporate-suffix vocabulary; near matches require review rather than fuzzy equality. Date comparison requires valid ISO dates. Ports use conservative text equality.

The required-breach-statement rule compares the guarantee's actual requirement with an extracted statement or an actual explicit absence notice. A null extracted statement alone cannot prove documentary absence. A notice that merely requests a statement is not proof of either compliance or absence.

Statuses are `MATCH`, `MISMATCH`, `MISSING_LEFT`, `MISSING_RIGHT`, `MISSING_BOTH`, `NOT_COMPARABLE`, `NEEDS_REVIEW`. A run is `CLEAN` only when all applicable rules match; supported mismatches produce `DISCREPANCIES_FOUND`, with any incomplete count still visible. Otherwise uncertainty produces `INCOMPLETE_EXAMINATION`. Failed output persistence retains a sanitized `FAILED` run and rolls back partial outputs.

## Versioned rules

Typed Pydantic configurations reject unknown document fields, playbooks, primitives, extra parameters, invalid tolerance policies and duplicate IDs. Ruleset `documentary-v1` has 41 unique definitions; shared LC definitions apply to both import and export:

| Playbook | Applicable rules | Checks |
| --- | ---: | --- |
| Import LC | 16 | LC/invoice currency, amount, beneficiary/seller, goods, quantity and shipment deadline; applicant/buyer/consignee; LC/packing and invoice/packing quantities; invoice/packing invoice reference; loading/discharge ports; three document-presence checks |
| Export LC | 14 | Shared LC comparisons; buyer/consignee; purchase order; invoice/origin exporter and goods; three presence checks |
| Documentary Collection D/A | 10 | Instruction versus invoice/bill of exchange: currency, amount, drawer/seller, drawee/buyer and presence |
| Performance Guarantee | 9 | Demand currency, amount cap, beneficiary, presentation before expiry, required breach statement; contract contractor/applicant and employer/beneficiary; demand/contract presence |

Import LC route fallback is allowed only when the current extracted route has exactly two ordered slash-separated ports; the comparison stores the original full fact, quote and derivation. Export beneficiary can use the explicitly configured extracted exporter role. No inference from case narrative, expected outcomes or reference labels.

Collection acceptance/maturity checks need actual events; those events are absent, so no acceptance or maturity result is fabricated. The known missing packing-list own reference is not a mismatch against another document's different reference.

## APIs and UI

Eight examination endpoints expose creation, history/latest/detail, rule results, findings, evidence relations and current facts; see README for paths. Start accepts an optional JSON request UUID. Unknown case/run/ownership returns 404; unsupported playbook 422; active run 409; database errors sanitized 503. Inputs-current compares current evidence/rules/threshold with the stored fingerprint without modifying history.

The case Examination tab offers explicit run/rerun, immutable history selection, counters, calculated findings, all rule results with filters, paired source evidence and expandable relations/current facts. Links use exact source version, extraction run and fact IDs in the existing PDF workspace. Reference findings/risks and expected decisions remain labelled separately.

## Source extraction repair

Phase 3 uses source-only bounded feedback when a null field has a unique printed label and nonempty value line in the actual native PDF. Feedback contains omitted field names, never expected label values. Supported fields are merged across the two bounded model attempts; contradictory supported values require review. Actual recovered dates/notice therefore originate in the source and retain page quotations. These repairs affect future extraction runs, not historical Phase 2 results.

## Evaluation and limits

The offline evaluator maps five meaningful documentary labels and excludes duplicate-invoice financing risk. Its primary unit is case/finding family, with exact normalized amount/quantity/date/PO checks. It separately publishes every raw finding, matched IDs, extra matching comparisons, misses and unmatched findings. One quantity label covers both LC/invoice and LC/packing comparisons; neither comparison is hidden. Breach absence uses a controlled semantic family because the reference wording differs from the actual document wording.

No OCR/vision capability is assumed. No risk APIs, final decisions, approval actions, RAG/embeddings/vector database, regulatory retrieval, Smart Insights, SWIFT/core trade or payments are included. The five-case synthetic evaluation is not a production accuracy benchmark.
