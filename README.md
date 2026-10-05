# FinArth Smart Trade

Phase 4 adds **auditable risk orchestration, replaceable synthetic providers and local duplicate trade checks** to the source-PDF and documentary examination workbench. Operational parties and current source facts produce separate risk signals with provider/policy provenance, immutable history and explicit unchecked or incomplete results. Runtime risk checks do not call the LLM or read risk-event/discrepancy ground truth.

**Synthetic Demo Data:** supplied fixtures are fictional. Preserve every **SYNTHETIC DEMO — NOT A FINANCIAL INSTRUMENT** marking. Expected PASS / REFER / BLOCK outcomes, reference findings/risks and approval events remain supplied references. Documentary examination is calculated separately and is not a final trade decision.

Phase 4 is on [`phase-4`](https://github.com/ahirm-finarth/smarttrade/tree/phase-4), based on validated [`phase-3`](https://github.com/ahirm-finarth/smarttrade/tree/phase-3). Earlier work remains on [`phase-2`](https://github.com/ahirm-finarth/smarttrade/tree/phase-2) and [`phase-1`](https://github.com/ahirm-finarth/smarttrade/tree/phase-1). See [Phase 4 architecture](docs/PHASE4_ARCHITECTURE.md), [actual Phase 4 validation](docs/PHASE4_VALIDATION.md) and [Phase 3 evidence](docs/PHASE3_VALIDATION.md).

## Native setup

Use Python 3.12+, uv, Node.js 20.9+ (verified with Node 22), npm, and the existing external MySQL 8-compatible database. No Docker or additional database service is used.

```sh
git clone --branch phase-4 https://github.com/ahirm-finarth/smarttrade.git
cd smarttrade
make setup
# Only if no credential file already exists:
cp .env.example .env
# Populate credentials privately, then:
make check-db
make migrate
make seed
make register-demo-documents
```

`make setup` installs locked Python dependencies into `backend/.venv` and locked Node dependencies into `frontend/node_modules`. Never overwrite an existing `.env` or reset the supplied database. Migrations use `smart_trade_alembic_version`, exclude unrelated tables, and add only Smart Trade-owned schema.

Registration copies and fingerprints the 18 committed PDFs, attaches them to the existing inventory, and creates immutable source versions. It is idempotent and **does not invoke the LLM**. Repeating the Phase 1 seed preserves registered sources. CSVs and the workbook remain deduplicated in `data/raw/`; source PDFs, case payloads, and the original manifest are in `data/demo/`. See [fixture notes](data/demo/README.md).

## Configuration

Backend settings read the ignored root `.env`; matching environment variables take precedence. Choose one database configuration family and remove unused placeholder keys.

| Purpose | Settings |
| --- | --- |
| Preferred MySQL URL | `DATABASE_URL` (MySQL only) |
| MySQL fields | `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` |
| Existing aliases | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |
| Document model | `LLM_API_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_PROTOCOL` |
| Local originals | `DOCUMENT_STORAGE_ROOT` (default `./storage`, relative to the repository root) |
| Intake limits | `DOCUMENT_MAX_BYTES=20971520`, `DOCUMENT_MAX_PAGES=100` |
| Examination confidence floor | `EXAMINATION_MIN_CONFIDENCE=0.85` (classification and fact confidence; no tuning to labels) |
| Model input bound | `DOCUMENT_MAX_TEXT_CHARS=60000` |
| Per-call timeout | `LLM_TIMEOUT_SECONDS=180` |
| Browser access | `CORS_ORIGINS` JSON array; both localhost and 127.0.0.1 on port 3000 by default |

A MySQL `DATABASE_URL` takes precedence; otherwise settings construct a PyMySQL URL with `utf8mb4`. Passwords use `SecretStr`, and SQL parameter logging is suppressed. A supplied `/v1` LLM base URL is treated as OpenAI-compatible; for another verified compatible endpoint set `LLM_PROTOCOL=openai`. Unknown protocols are refused. Structured calls request JSON Schema and strictly validate returned JSON before persistence. Truncated responses get one bounded larger-budget retry. Startup, health, case queries, registration, and default backend tests do not invoke the model.

The supplied endpoint does not declare vision capability. Pages with insufficient native text become `NEEDS_REVIEW` with an `OCR_REQUIRED` reason; no OCR, vision request, or guessed text is produced. Oversized model input also requires review rather than silent truncation.

Only `NEXT_PUBLIC_API_BASE_URL` belongs in `frontend/.env.local` or the environment before building Next.js; it defaults to `http://localhost:8000` and is fixed at build time. Keep all backend credentials out of frontend configuration. The upload UI reflects the default 20 MB limit; when changing backend limits, update that user-facing limit as well. `GH_TOKEN` is only for Git authentication and is not an application setting. Remotes contain no token.

## Run and use

Run in separate terminals from the repository root:

```sh
make backend
```

```sh
make frontend
```

- Dashboard: http://localhost:3000/
- Case workspace: `/cases/{case_id}`; select **Documents**, **Examination** or **Risk & Compliance**.
- Document workspace: `/documents/{document_id}` (the internal numeric inventory ID).
- Backend health: http://localhost:8000/health
- API documentation: http://localhost:8000/docs

Upload a valid PDF, then select **Process**. Open a document and select a field to inspect its normalized value, raw source value, source quotation, confidence, version, page, and run. The preview renders the real PDF page; **Open original PDF** serves the immutable original. A native-text transcript also highlights an exact raw-text match. No bounding boxes are inferred.

Use **Reprocess** for a new extraction run on the same original, or **Source details and new version** to upload another immutable version. Earlier runs and versions remain selectable. Failed and review-required states are explicit. Progress is polled from committed stages, without fabricated percentages. The API processes synchronously in a native worker; refresh does not erase saved state. A crashed worker's active run expires after 30 minutes and is marked failed on the next explicit retry. This is not a distributed job queue.

For production frontend validation:

```sh
make build
npm --prefix frontend run start -- --hostname 127.0.0.1
```

Development and production builds explicitly use Next.js's supported Webpack builder. Turbopack's CSS worker attempted a denied local port binding in this execution environment; Webpack builds and serves the same application natively.

## Document architecture

```text
Case → CaseDocument → DocumentVersion → immutable source PDF
                         ├─ DocumentPage (native text, 1-based page)
                         └─ DocumentProcessingRun (stages, model, prompt versions)
                              └─ ExtractedFact (raw/normalized value, page, quote, confidence)
```

Four additive tables were introduced by Alembic revision `e52fad8ad293`, following `30af12917573`:

- `smart_trade_document_versions`: inventory/case links, version, filename, relative storage key, size, MIME, SHA-256, status, page count, timestamps.
- `smart_trade_document_pages`: immutable page text, length, native extraction method, review flag.
- `smart_trade_document_processing_runs`: version/run sequence, persisted state, parser/model, classification, timestamps, safe failure message, prompt/stage metadata.
- `smart_trade_extracted_facts`: run link, field, raw and normalized values, JSON value, page, quotation, confidence, evidence status, review reason.

Fact ownership is derived through run → version → document → case, avoiding inconsistent duplicated ownership. Fact API responses also include those explicit identifiers. Money normalization uses `Decimal`; date, quantity/unit, and boolean normalization are deterministic. Unsupported or ambiguous values remain flagged.

The shared LLM client, classifier, type-specific schemas, extraction prompt, normalization, evidence validation, storage, and processing service are separate from thin API handlers. Classification uses page-heading cues followed by a real model call. Extraction receives only page text and a document-specific schema. Absent fields remain null. See [supported schemas and validation](docs/PHASE2_VALIDATION.md).

Evidence must match native page text. If the model quotes only a field label, a unique adjacent native value may supply the exact quotation; money/date/quantity representations must normalize identically. This never uses reference datasets. Ambiguous labels, unrelated values, invented quotations, and unequal amounts cannot pass. Model originals and the reconciliation method are retained in run metadata. One additional model extraction attempt may repair unsupported evidence; remaining unsupported facts stay `NEEDS_REVIEW`.

Originals live under ignored `storage/cases/<internal-case-id>/documents/<internal-document-id>/versions/<version>/<uuid>/source.pdf`. Storage keys are generated internally; filenames are sanitized and never used as paths. Intake verifies MIME, signature, PDF validity, size/pages, and encryption, computes SHA-256, and rejects exact duplicates within a case. Originals use exclusive creation and read-only file permissions; integrity is checked before processing or serving. A malware-scanner extension point is documented before storage, without adding unsupported infrastructure.

## API

Existing case/dashboard APIs remain compatible. Document APIs are additive:

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/api/v1/cases/{case_id}/documents` | Inventory with detected type, version/pages, status, update time |
| POST | `/api/v1/cases/{case_id}/documents` | Multipart `file`; optional `document_id` adds a version to an existing inventory entry |
| GET | `/api/v1/documents/{document_id}` | Versions, selected pages/run/facts, history; optional `version_id` or `run_id` |
| POST | `/api/v1/documents/{document_id}/process` | Process selected/latest version; reuse an already completed run |
| POST | `/api/v1/documents/{document_id}/reprocess` | New run; preserve earlier facts and history |
| GET | `/api/v1/documents/{document_id}/processing-runs` | All version/run history |
| GET | `/api/v1/documents/{document_id}/facts` | Latest run facts; optional `run_id` selects history |
| GET | `/api/v1/documents/{document_id}/source` | Original PDF; optional `version_id` |
| GET | `/api/v1/documents/{document_id}/pages/{page_number}/image` | Size-bounded PNG preview of the actual source page; optional `version_id` |

Processing POSTs accept optional `version_id`. A completed processing HTTP request may return a persisted `FAILED` or `NEEDS_REVIEW` run; clients must inspect its state. Unknown case/document/version/run/page returns 404. Invalid intake returns 422; concurrent processing or conflicting ownership returns 409; database failures return sanitized 503 responses. A run ID from another document cannot select its facts. Storage paths and credentials are never API response fields.

Existing routes also provide `/cases`, `/cases/{case_id}`, `/dashboard/summary`, and each case's parties, trade-lines, discrepancies, risk-events, and approvals under `/api/v1`. Health requires MySQL, reports only safe readiness/configuration flags, and does not depend on LLM availability. Decimal API values are strings; displayed persistence and event timestamps use IST.

## Demo processing and evaluation

These are separately invoked development commands:

```sh
make register-demo-documents      # No model calls
make process-demo-documents       # Actual model calls, source PDFs only
make evaluate-demo-extraction    # Labels used only here; ignored local JSON report
# Explicitly create new runs, optionally for one case:
backend/.venv/bin/python -m app.scripts.process_demo_documents --reprocess --case-id ST-BG-2026-0005
```

Evaluation covers document type/reference and unambiguous document-specific monetary, quantity/unit, and goods labels. It does not compare trade documents with each other or generate compliance findings. Missing outputs count as misses. Unsupported evidence is not counted as a supported extraction. Document dates and other unlabelled fields are reported as unscored; evaluation does not invent ground truth. [Phase 2 validation evidence](docs/PHASE2_VALIDATION.md) records actual live results and limitations.

## Checks

```sh
make test          # Isolated tests; no live model calls; MySQL checks skipped
make test-mysql    # External MySQL schema, persisted evidence routes and seed regression
make lint
make typecheck
make build
make secrets
python3 scripts/check_secrets.py --history --frontend-build
make check-llm     # Model-list health probe only
```

For browser tests, register and explicitly process at least one demo PDF first, keep the backend running, and install Playwright Chromium once:

```sh
cd frontend && npx playwright install chromium
cd ..
make test-e2e
```

Desktop/mobile tests cover Phase 1 dashboard/filter/tab/keyboard regressions plus duplicate upload, real PDF previews, field/source provenance, recoverable processing errors, and unknown documents. Default browser tests make no live model calls. Screenshots/traces are ignored. Backend isolation uses temporary SQLite only in tests; production uses MySQL and Alembic, never `create_all()`.

The secret scanner checks configured credential material, GitHub token patterns, and tracked environment files without printing matching content. Optional modes check historical blobs and compiled frontend artifacts. Runtime originals, reports, credentials, and dependency caches are ignored; reproducible synthetic PDFs are committed.

## Repository layout

```text
frontend/app/                    Dashboard, case tabs, document workspace, error states
frontend/components/             Existing ledger UI plus intake, status, document/fact panels
frontend/lib/                    Central typed API client and exact value formatting
frontend/tests/                  Desktop/mobile browser workflows
backend/app/api/v1/              Thin case and document routes
backend/app/models/               Case domain and version/page/run/fact persistence
backend/app/schemas/              API contracts and type-specific structured output schemas
backend/app/services/             Registration, parsing pipeline, classification/extraction, evidence
backend/app/integrations/         Shared LLM client, native PDF parser, local storage abstraction
backend/app/scripts/              Seed, register/process/evaluate demo, safe diagnostics
backend/alembic/                  Scoped additive migrations
backend/tests/                    Isolated and separately invoked MySQL regression tests
data/raw/                         Original matching CSV/XLSX reference datasets
data/demo/                        Original synthetic PDF packets, JSON payloads, manifest
storage/                          Ignored runtime originals
reports/local/                    Ignored evaluation output
docs/                             Phase 1 and Phase 2 evidence
```

[DESIGN.md](DESIGN.md) and `.impeccable/design.json` preserve the established operations design system. Phase 1 verification remains in [docs/PHASE1_VALIDATION.md](docs/PHASE1_VALIDATION.md).

## Deferred scope

Phase 4 stops at separate risk signals, synthetic providers and explainable local duplicate candidates. Phase 5 or later owns final PASS / REFER / BLOCK decisions, the combined documentary/risk matrix, maker/checker actions, overrides, delegated authority, approval matrices, payment release, SWIFT/core trade posting, EDPMS/IDPMS, real sanctions/vessel/fair-value vendors, regulatory RAG/UCP/ISBP retrieval, MiniLM/embeddings/vector databases, Smart Insights and post-event monitoring. OCR/vision, cloud storage, distributed processing, richer multi-line schemas, facility/credit controls and production access controls require later work.

## Phase 3 examination

After explicitly processing the actual originals, select **Examination** and **Run examination**. Review findings and all rule results; select **View evidence** to see expected/governing and observed facts, their raw/normalized values, quotes, page, confidence, rule ID/version and comparison result. Source links open the exact historical document version/run/fact. Expand **Evidence relations** and **Current extracted facts** for the underlying ledgers.

**Rerun examination** creates a new stored run. History selection keeps old results intact. Changed source facts/rules/threshold show a stale-input notice. Missing or low-confidence evidence stays incomplete; it does not create a business mismatch. A failed connection should be followed by **Refresh history** before retrying; retries use the same request UUID to avoid duplicating uncertain submissions.

```sh
make examine-demo-cases             # Deterministic DB facts/rules only; new stored runs
make evaluate-demo-examination     # Offline labels; local JSON and Markdown reports
# Or examine one operational case:
backend/.venv/bin/python -m app.scripts.examine_demo_cases --case-id ST-EXP-2026-0003
```

Examination routes:

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/v1/cases/{case_id}/examinations` | Run; optional JSON `request_id` UUID for submission deduplication |
| GET | `/api/v1/cases/{case_id}/examinations` | Stored history |
| GET | `/api/v1/cases/{case_id}/examinations/latest` | Latest stored detail |
| GET | `/api/v1/examinations/{run_id}` | Immutable detail plus current-input flag |
| GET | `/api/v1/examinations/{run_id}/rule-executions` | Full rule results and two resolved inputs |
| GET | `/api/v1/examinations/{run_id}/findings` | Calculated supported documentary findings |
| GET | `/api/v1/cases/{case_id}/evidence-relations` | Latest or `run_id`-selected relations |
| GET | `/api/v1/cases/{case_id}/extracted-facts` | Latest source/run facts, provenance and threshold |

Ruleset `documentary-v1`: 41 unique definitions; Import LC 16, Export LC 14, Collection D/A 10, Guarantee 9 applicable rules. Four additive MySQL tables store examinations, executions, relations and calculated findings separately from the original reference inventory. No graph database or new infrastructure is required.

Live validation detected four of five documentary reference families (five raw findings); guarantee demand classification confidence 0.72 falls below 0.85, leaving six guarantee comparisons for review. Precision 1.0000, recall 0.8000, F1 0.8889 on this small synthetic set. The packing-list reference extraction miss remains unchanged. This is not a production accuracy or final-decision claim.

## Phase 4 risk and compliance

Select **Risk & Compliance** and explicitly **Run risk checks**. Review category results, detected findings and individual provider checks. **View risk evidence** pairs the originating operational party/source fact with the provider's mock reference, result, rule ID/version and severity. Document links select the exact historical source version, extraction run and fact. Provider result details retain duplicate candidate identities, matched/different fields and their source evidence. The independent financing rule result remains visible in the risk execution audit.

**Rerun risk checks** creates a new run. Select earlier runs from history; changes to current facts, provider configuration or rules show a stale-input notice. Completed means execution finished. A provider's clear result applies only to its configured synthetic list or local search; it does not clear the transaction. Missing references are **Not checked**, absent optional subjects **Not applicable**, uncertain evidence **Insufficient data**, and failed providers **Provider error**. Refresh history before retrying an uncertain submission; retries retain their request UUID. Active synchronous workers expire after five minutes; this is a native demo worker, not a distributed queue.

```sh
make run-demo-risk                  # New stored runs; operational inputs only
make evaluate-demo-risk             # Offline labels; ignored JSON and Markdown reports
backend/.venv/bin/python -m app.scripts.run_demo_risk --case-id ST-IMP-2026-0002
```

Seven provider categories share strict `RiskProvider`, `ProviderInput` and `ProviderResult` contracts. Four synthetic lookup providers read only `reference_screening.csv`; the duplicate provider compares current stored invoices; goods and fair-value providers accept explicit typed `GoodsPolicy` and `PriceBand` configurations. The default registry has no invented country/goods policy or price band. To replace a provider, implement `check()` and a credential-free versioned `snapshot()`, inject a `ProviderRegistry` into orchestration and test it before changing the default registry. No browser provider credentials or arbitrary evaluation handlers are supported.

Eight routes under `/api/v1`:

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/cases/{case_id}/risk-runs` | Explicit run; optional JSON `request_id` UUID |
| GET | `/cases/{case_id}/risk-runs` | History |
| GET | `/cases/{case_id}/risk-runs/latest` | Latest detail |
| GET | `/risk-runs/{run_id}` | Stored detail plus current-input flag |
| GET | `/risk-runs/{run_id}/provider-checks` | Provider inputs/results |
| GET | `/risk-runs/{run_id}/rule-executions` | Versioned risk policy audit |
| GET | `/risk-runs/{run_id}/findings` | Calculated risk signals |
| GET | `/cases/{case_id}/duplicate-candidates` | Read-only current cross-case search |

Ruleset `risk-v1` has eight rules across screening, country, port, vessel, duplicate, goods and fair value. The five demo cases yield three supported signals on the risk Import LC and zero material risk findings on the other cases. Independent evaluation: TP 3, FP 0, FN 2; precision 1.0000, recall 0.6000, F1 0.7500. The supplied fair-value label lacks a price band, and the labelled historical invoice is absent from stored cases. Both remain counted misses; no price, historical invoice or financing event is fabricated.
