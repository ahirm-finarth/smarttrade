# Phase 4 architecture

Phase 4 extends the existing native FastAPI/MySQL/Next.js application. Operational party identities and current Phase 2 source-derived facts enter provider checks; deterministic versioned policy interprets those results into separate risk findings. Phase 3 documentary findings remain separate. No combined decision, approval action, live vendor, model inference or new infrastructure is introduced.

```text
Operational parties + current PDF-derived facts
  → strict provider inputs + immutable configuration/input snapshot
  → synthetic lookups / deterministic local duplicate search / typed trade policy
  → provider-check audit
  → risk-v1 policy execution audit
  → supported risk findings + originating source/provider/rule evidence
```

## Persistence and run lifecycle

Alembic revision `e32819e0cf3f` follows Phase 3 `4c4c93c90831`. Four additive, indexed utf8mb4 tables:

- `smart_trade_risk_runs`: case/run and case/request uniqueness, ruleset/provider versions, input fingerprint, immutable input/configuration snapshot, timestamps, summary and sanitized failure.
- `smart_trade_provider_checks`: run/case ownership, unique run/check key, provider category/name/version, full safe input/result and timestamps.
- `smart_trade_risk_rule_executions`: unique run/check/rule, policy ID/version, complete rule/input/output snapshots.
- `smart_trade_detected_risk_findings`: case/run/check/execution links, category/type, severity, subject, rule ID/version and source/provider/candidate evidence JSON.

The case row lock serializes run creation; UUID submissions deduplicate uncertain retries. A RUNNING lease younger than five minutes returns 409. An expired worker is retained as FAILED before a new numbered run is created. RUNNING is committed before checks; check/execution/finding outputs commit together. Persistence failure rolls those outputs back and retains a sanitized FAILED run. Earlier completed rows are never recalculated or overwritten.

COMPLETED means checks finished; PARTIAL means at least one provider error or insufficient input; FAILED means outputs could not be persisted. Review signals do not make execution fail. Every response keeps `decision_computed=false`. Current-input checks rebuild fingerprints without changing historical snapshots.

## Replaceable providers and provenance

`RiskProvider` exposes category/name/version, `check(ProviderInput)` and credential-free `snapshot()`. The registry refuses duplicate categories. Frozen extra-forbidden Pydantic models validate inputs, references and results. Recursive checks reject credential-like metadata before audit persistence; an invalid provider result becomes a sanitized PROVIDER_ERROR. A missing or malformed synthetic reference file also produces auditable provider errors while independent local checks continue.

Provider states: CLEAR, POTENTIAL_MATCH, HIT, NEEDS_REVIEW, NOT_CHECKED, NOT_APPLICABLE, INSUFFICIENT_DATA and PROVIDER_ERROR. HIT is a provider signal, never a transaction decision. The default synthetic lookup deliberately maps active review records to review/potential-match states.

| Provider | Implementation / actual default scope |
| --- | --- |
| Screening | `SyntheticScreeningProvider`; financial party rows, conservative normalized names and supplied fictional counterparty reference |
| Country | `SyntheticCountryRiskProvider`; operational party country codes and source certificate origin; no supplied country-policy row, so unchecked |
| Port | `SyntheticPortRiskProvider`; trusted current bill-of-lading loading/discharge facts and fictional route reference |
| Vessel | `SyntheticVesselRiskProvider`; trusted current bill-of-lading vessel fact and fictional vessel reference |
| Duplicate | `LocalDuplicateTradeProvider`; current cross-case stored invoice profiles and SHA-256 |
| Goods | `SyntheticGoodsRiskProvider`; explicit typed `GoodsPolicy` rows only; empty default |
| Fair value | `SyntheticFairValueProvider`; explicit typed `PriceBand` rows only; empty default |

Party input snapshots allow only row ID, role, name and country; supplied `screening_status` is excluded. Matching trustworthy source facts attach exact historical fact/run/version/page, raw/normalized value, quote and confidence. A stored party row is itself explicit operational provenance when no matching PDF fact exists; no quotation is invented. Routes/vessels/prices use the current source resolver and confidence floor 0.85, including source-quote revalidation. Failed latest extraction never falls back to obsolete trusted facts.

Only `reference_screening.csv` is consumed by mock lookup providers. Its `ZZ` country is fictional reference metadata, not an identity discriminator or geopolitical claim. Screening exact matches use conservative party aliases. Optional similarity uses SequenceMatcher ≥0.90 with a word-count difference ≤1; this yields POTENTIAL_MATCH requiring analyst validation, not confirmed identity. No MiniLM, embeddings or vector search is used.

## Duplicate search

One bounded select-in batch loads current cases, parties, documents, versions, pages, runs and facts. The shared Phase 3 evidence builder is reused unchanged. Profiles contain invoice ID, seller, buyer, amount/currency, optional purchase-order reference, source IDs/evidence and SHA-256. Money uses Decimal; identifiers and party aliases use deterministic normalization. Complete identity profiles also receive a canonical commercial SHA-256 fingerprint.

Exclude the current case and the same document. Compare across actual stored current cases in this order:

| Match | Finding / evidence grade |
| --- | --- |
| Exact file SHA-256 | EXACT_FILE_DUPLICATE / 1.00 |
| Complete commercial fingerprint | DOCUMENT_DUPLICATE_CANDIDATE / 0.97 |
| Invoice + seller + buyer + currency + amount | Candidate / 0.95 |
| Invoice + seller + buyer | Candidate / 0.80 |
| Invoice + seller + currency + amount | Candidate / 0.85 |

Grades are configured evidence ranks, not probabilities. Every candidate identifies its actual case/document/version, matching/differing fields and candidate source chain. Same seller/amount without invoice identity is insufficient. Reprocessing/version history is excluded as repeated financing. A new candidate document version retires prior current evidence while old risk snapshots remain selectable.

File duplication and document identity never establish financing or fraud. `RISK-DUP-FINANCE-001` requires an independently evidenced FINANCED event with event ID/source. The current application has no financing/presentation event ledger; all runtime financing checks stay NOT_CHECKED. The labelled HIST-INV-OB-2025-889 is absent from stored cases and is not materialized to replay ground truth.

## Trade policy and versioned rules

Goods policies match explicit normalized descriptions and carry reference ID, status and rationale. The default has no legal or dual-use classification mapping. Price bands contain reference ID, exact goods, currency, quantity unit and finite ordered min/max Decimal prices. Prefer the source unit price; otherwise derive total/quantity with recorded operands. Require positive quantity and matching currency/unit; no FX or unit conversion is inferred. Missing or ambiguous inputs remain incomplete; missing bands are unchecked. Unit tests inject explicitly synthetic bands, but no invented benchmark ships for the demo goods.

Ruleset `risk-v1`: eight version-1 policies, with configured severity. Screening, country, port, vessel, goods and price each have one SIGNAL rule. Duplicate has a document-candidate rule and a separate independently evidenced financing rule. Only SIGNAL, DUPLICATE and FINANCING_EVENT handlers are allowed. Unknown handlers refuse execution; invalid configurations are rejected. Provider errors/insufficient states propagate into policy audits and never become clear results.

## API, UI and isolated evaluation

Thin risk routes expose explicit runs/history/detail, provider checks, rule executions, findings and read-only duplicate candidates. See [README route table](../README.md#phase-4-risk-and-compliance). Unknown ownership returns 404, bad request payloads 422, active workers 409, and database failures sanitized 503.

The Risk & Compliance tab reuses the operations ledger: run/history controls, category/check ledgers, findings, source/provider/policy evidence pairs and expandable rule audit. Mobile evidence stacks; wide audit tables scroll inside the ledger. Selected tabs are revealed within their strip without changing vertical position. No calculated final clearance or approval controls appear.

`run_demo_risk` reads operational DB cases and creates runs without labels. `demo_risk_evaluation` is imported only by the separately invoked evaluator/tests. It reads risk-event/discrepancy ground truth after execution; expected decisions never enter provider or rule logic. All in-scope positives count, including unavailable benchmark/history misses. Export post-event monitoring and guarantee documentary conditions are explicitly excluded by scope. Small synthetic-set metrics are validation evidence, not production accuracy.
