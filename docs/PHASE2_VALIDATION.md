# Phase 2 implementation and validation

Verified on 5 October 2026 against the native Python/Node application, supplied external MySQL and configured external LLM. All fixtures remain visibly synthetic. The requested delivery branch is [`phase-2`](https://github.com/ahirm-finarth/smarttrade/tree/phase-2), based on Phase 1 commit `53c6246`.

## 1. Architecture added

The existing case register now owns immutable document versions. Each version owns page-level native PDF text and append-only processing runs; each run owns extracted facts. Separate storage, PDF parser, classifier, schema-specific extractor, normalizer and evidence validator services feed thin FastAPI handlers. The existing Phase 1 LLM client supplies strictly validated JSON output. Only actual PDF page text reaches classification/extraction; reference CSV/XLSX/JSON content is confined to developer evaluation.

Processing commits `PARSING`, `PARSED`, `CLASSIFYING`, `EXTRACTING` and terminal `COMPLETED`, `FAILED` or `NEEDS_REVIEW` states. Row locking serializes run creation. Reprocess retains earlier runs/facts; repeated Process reuses a completed run. Source versions and their pages remain immutable. Prompt assets are recorded as `classification-v1` and `extraction-v2`; parser/model/stages and evidence reconciliation are traceable in run metadata.

## 2. Tables and migrations

Alembic revision `e52fad8ad293` follows the Phase 1 revision `30af12917573`. It adds four MySQL-compatible tables without modifying unrelated database tables:

| Table | Purpose |
| --- | --- |
| `smart_trade_document_versions` | Case/document foreign keys, version sequence, filename, internal storage key, SHA-256, size/MIME, pages, status and timestamps |
| `smart_trade_document_pages` | Version/page uniqueness, native text, text length/method and review flag |
| `smart_trade_document_processing_runs` | Version/run uniqueness, status, parser/model, document classification/confidence, safe error, timestamps and JSON metadata |
| `smart_trade_extracted_facts` | Run/field uniqueness, raw/normalized values and JSON, page, quote, confidence and review status/reason |

Fact ownership derives through run → version → document → case; the API exposes these identifiers explicitly. Text/JSON columns avoid oversized VARCHAR rows. The migration was applied to external MySQL; Alembic autogeneration reported no pending operations. The scoped `smart_trade_alembic_version` table and existing Phase 1 data are retained.

## 3–4. Supported types and extraction fields

These ten classes occur in the supplied 18 PDFs. `OTHER` is a classification fallback that requires review, not a fabricated extraction schema. Money values include currency; quantities include units. Every non-null field requires raw text, a 1-based page, quotation and confidence. Absent fields remain null.

| Type | PDFs classified | Schema fields |
| --- | ---: | --- |
| `LETTER_OF_CREDIT` | 3 | lc_number, applicant, beneficiary, exporter, buyer, amount, goods_description, quantity, latest_shipment_date, port_of_loading, port_of_discharge, route, purchase_order_reference |
| `COMMERCIAL_INVOICE` | 4 | invoice_number, seller, buyer, goods_description, quantity, unit_price, total_amount, purchase_order_reference |
| `PACKING_LIST` | 2 | document_number, invoice_number, goods_description, quantity, packages |
| `BILL_OF_LADING` | 3 | bl_number, vessel_name, shipment_date, port_of_loading, port_of_discharge, consignee |
| `CERTIFICATE_OF_ORIGIN` | 1 | certificate_number, exporter, goods_description, country_of_origin |
| `BILL_OF_EXCHANGE` | 1 | bill_number, drawer, drawee, amount, tenor |
| `COLLECTION_INSTRUCTION` | 1 | collection_reference, drawer, drawee, collection_type, amount, maturity_date, release_condition |
| `BANK_GUARANTEE` | 1 | guarantee_number, applicant, beneficiary, amount, expiry_date, required_demand_conditions |
| `GUARANTEE_DEMAND` | 1 | demand_reference, beneficiary, demand_amount, demand_date, notice, breach_statement |
| `CONTRACT_EXTRACT` | 1 | contract_reference, project, contractor, employer |

Schema support does not imply every printed field was returned by the model. Omitted fields remain absent rather than being populated from labels. Explicit breach statements are extracted only when present.

## 5. Local storage and provenance

`DOCUMENT_STORAGE_ROOT` defaults to repository-relative `./storage`. A filesystem implementation behind a storage protocol uses generated internal case/document/version/UUID paths. Sanitized filenames are display metadata. Intake bounds size (20 MB by default) and pages (100), validates PDF signature/MIME/content, rejects encrypted/damaged PDFs and computes SHA-256. Exact hashes deduplicate within a case. Exclusive creation and read-only permissions preserve originals; hashes are checked before processing and serving. Traversal and escaping symlinks are rejected. Runtime storage is ignored; reproducible originals remain committed under `data/demo/case_packets`. A scanner extension point exists before storage.

Normalization uses Decimal money, explicit currency, unambiguous dates, quantity/unit and explicit boolean terms. Source validation requires both the quote in its page and raw value in the quote. A label-only quotation can be anchored to its unique adjacent native PDF row only when the proposed value matches verbatim or through equal deterministic money/date/quantity normalization. The original model response values and anchoring method remain in metadata. Unequal amounts, ambiguous labels and invented snippets cannot pass. Unsupported evidence and low confidence require review. No source coordinates are invented.

## 6. API routes

| Method | Route | Result |
| --- | --- | --- |
| GET | `/api/v1/cases/{case_id}/documents` | Extended source inventory |
| POST | `/api/v1/cases/{case_id}/documents` | PDF upload; optional document_id adds an immutable version |
| GET | `/api/v1/documents/{document_id}` | Document, versions, pages, runs and selected facts |
| POST | `/api/v1/documents/{document_id}/process` | Persisted processing result |
| POST | `/api/v1/documents/{document_id}/reprocess` | New preserved run |
| GET | `/api/v1/documents/{document_id}/processing-runs` | Version/run history |
| GET | `/api/v1/documents/{document_id}/facts` | Latest or selected run facts |
| GET | `/api/v1/documents/{document_id}/source` | Integrity-checked original PDF |
| GET | `/api/v1/documents/{document_id}/pages/{page_number}/image` | Size-bounded PNG rendered from the actual PDF |

Version/run selectors validate ownership. Unknown resources return 404; invalid intake 422; concurrent/conflicting requests 409; unavailable persistence 503. Processing returns its actual persisted terminal state, including failures. Storage paths and credentials are not response fields. Existing case APIs retain compatibility.

## 7. UI routes and components

The Documents tab at `/cases/{case_id}?tab=documents` contains `DocumentInventory`: upload, process/reprocess, detected type, source version/pages, processing/extraction status and timestamps. `/documents/{document_id}` contains `DocumentWorkspace`: real PDF page preview/original link, native transcript, selectable facts, exact raw/normalized values, source quotation, confidence and version/run history. Supporting typed API functions, `DocumentStatus` and provenance views extend the incumbent ledger design.

Desktop displays source and facts together. Mobile places facts/provenance before the source and contains wide inventories. Clicking a fact selects its originating page and quotation. Persisted progress is polled without invented percentages. Error/review/empty states, duplicate upload confirmation, native file controls, keyboard navigation and preview retry are implemented. An explicit Refresh remounts a failed preview; stale refresh requests cannot clear a newer processing/upload error. Synthetic markings remain visible in both application and originals. “Source matched” describes quotation support, not a trade decision.

## 8–11. Actual demo and evaluation results

Registration: **18 source PDFs** attached to existing inventory entries; repeated registration reported 18 already registered and created no duplicate entries. The deduplicated CSV/workbook inputs stay in `data/raw`; PDFs, original manifests and five case JSON payloads are in `data/demo`. No extracted ZIP duplicate was committed. Largest supplied PDF: 6,227 bytes.

Latest live batch: **18/18 completed**, 18 native-text pages, **105/105 persisted facts supported by source text**. All stored original hashes were checked against their committed fixture bytes; every supported quotation/value was checked against the stored page. All ten classifications are represented in the table above.

The checked-in [evaluation snapshot](phase2-demo-evaluation.json) records actual results:

| Labelled metric | Correct / labelled |
| --- | ---: |
| Document classification | **18 / 18** |
| Document reference exact match | **17 / 18** |
| Normalized amount + currency | **8 / 8** |
| Quantity + unit | **8 / 8** |
| Goods description | **8 / 8** |

The missing reference is `document_number` in `Packing_List_PL-NT-260101.pdf`: the PDF prints `PL-NT-260101`, but the model omitted that field. The invoice reference, goods, quantity and packages extracted from that PDF have valid provenance. This omission is counted as a miss; completion indicates the extracted facts passed validation, not exhaustive recall.

Dates are **unscored** because supplied reference datasets provide no document-date ground truth. Other unlabelled fields and multi-line items are also unscored. Scores cover only the supplied labelled development fixtures; no wider accuracy claim is made. Missing supported outputs count as misses. Evaluation never performs cross-document trade checks.

## 12–14. Executed validation and live LLM evidence

| Check | Result |
| --- | --- |
| Original Phase 1 tests before implementation | 19 passed, including external MySQL |
| Final backend suite with external MySQL | **56 passed** |
| Desktop/mobile Playwright workflows | **6 passed** |
| Ruff checks and formatting | Passed |
| Frontend ESLint | Passed |
| Next route generation and TypeScript | Passed |
| Native Next production build | Passed using supported Webpack builder |
| Alembic upgrade and drift check | Applied; no pending operations |
| Demo registration and repeat registration | 18 registered; repeat idempotent |
| Actual configured LLM processing | 18 PDFs completed; persisted source-only facts in MySQL |
| Live production-browser acceptance | Case → invoice → Reprocess → real LLM/MySQL → selected amount quotation/version/page/run verified; six supported invoice facts and prior history retained |
| Original integrity and supported provenance audit | 18 originals and 105 facts passed |
| Secret checks | Tracked files, staged additions, Git history and frontend build checked before delivery |

Backend coverage includes storage traversal/symlink safety, MIME/signature/limits, native PDF parsing, strict classification/extraction schemas, output-budget retries, Decimal/date/quantity normalization, source anchoring positive/negative cases, duplicate upload, source PDF/PNG, ownership checks, version/run preservation, failed/review/concurrent processing, registration idempotency, seed preservation and label-only evaluation. Default tests mock the model; external MySQL checks are explicit.

Browser coverage includes Phase 1 dashboard/filter/case/tab/keyboard regressions, duplicate PDF intake, actual source rendering, API-backed field provenance and exact strings, viewport containment, transient preview failure followed by a successful Refresh, recoverable process failure and unknown-document routing. Captures were reviewed together on desktop and mobile. Independent finish review checked persistence, fidelity, ceiling, material fixes and keep decisions; its preview recovery finding was corrected and regression-tested.

The separate live browser acceptance used `Commercial_Invoice_INV-CE-260401.pdf` in `ST-COL-2026-0004`, opened from the case inventory. Reprocess created a new completed run using the real configured endpoint; selecting total_amount showed the same source quotation and version/page/run as the persisted API fact. This live check was explicit; default browser tests retain mocked model failures. The evaluation snapshot and all-original/all-fact provenance audit were refreshed after this run. The documenter confirmed the inherited design system matches and preserved DESIGN.md and its sidecar.

Live model checks initially exposed response truncation and label-only quotes. Focused fixes added bounded budgets/retries and source-only native-row reconciliation. Earlier failed/review runs remain in history. A validation-worker restart was recorded explicitly as a failed run before retrying; no database reset or erased history was used. All final latest runs completed with schema validation and source support. Native-text-poor PDFs stop for review without an unsupported vision call.

## 15–17. Git delivery

The Phase 2 branch contains these small Conventional Commit steps, each validated, checked for secrets and pushed:

1. `d0cca1e` — chore(data): add reproducible Smart Trade demo document fixtures
2. `ea2e64e` — feat(documents): add versioned document storage and processing schema
3. `b351e5e` — feat(documents): add page-aware PDF parsing and fingerprinting
4. `82b114e` — feat(ai): add schema-validated trade document classification
5. `0cbaaf9` — feat(ai): add provenance-backed trade document field extraction
6. `55ce559` — feat(evidence): normalize extracted trade facts and validate provenance
7. `00348f0` — feat(api): expose Smart Trade document processing endpoints
8. `695ad64` — feat(demo): add reproducible document processing and extraction evaluation
9. `d3f07c7` — fix(ai): bound retries for truncated output and unsupported source quotes
10. `07d4bb1` — fix(evidence): reconcile model labels with exact native PDF rows
11. `8e4416b` — feat(api): serve source page previews and explicit fact provenance
12. `ecfbbf6` — feat(web): add trade document intelligence workspace
13. `3a6cb5f` — fix(web): restore document preview and preserve newer error states
14. test(phase2): record verified document intelligence and demo results

The last two commits include the recovery regression and this report. Their hashes are available in the [branch history](https://github.com/ahirm-finarth/smarttrade/commits/phase-2). The user's explicit separate-branch request supersedes the pasted template's `origin/main` target. Delivery uses **origin/phase-2**, with local/remote heads compared and a clean working tree confirmed after the final push. Phase 1 remains available on its own branch. Credentials, `.env`, runtime storage, caches and browser traces are excluded; the remote URL contains no token.

## 18. Intentional limits and Phase 3 boundary

Phase 2 provides individual-document facts and source provenance. Evidence graphs, cross-document amount/quantity/date/party comparisons, documentary discrepancies, UCP/ISBP, sanctions/vessel/country/price risk, decision matrices, PASS/REFER/BLOCK calculation, maker/checker actions, Smart Insights, SWIFT and core posting remain deferred. Existing findings/outcomes/events are passive synthetic references.

Source storage is local; no cloud storage or malware service was introduced. Processing is synchronous and bounded rather than a distributed queue. The supplied endpoint does not declare vision support, so scanned/text-poor pages require review; no OCR stack was installed. The narrow schemas extract scalar values rather than arbitrary multi-line items. The model may omit printed optional fields, as the recorded packing-list miss demonstrates. No advanced annotation engine or invented bounding boxes was added. The application continues to run natively without Docker.
