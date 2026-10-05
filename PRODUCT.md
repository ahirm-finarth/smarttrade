# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

User-specified Next.js App Router, TypeScript, Tailwind CSS; Python 3.12+ FastAPI, Pydantic, SQLAlchemy, Alembic; externally supplied MySQL.

## Users

Trade operations users inspecting synthetic trade cases and their related records in an enterprise operations interface. Phase 5 adds explicit demo maker, checker, trade, compliance, legal and supervisor roles; production identity remains out of scope.

## Product Purpose

FinArth Smart Trade is an evidence-led, governed trade-finance decision layer. Phase 1 establishes the persisted case inventory and dashboard. Phase 2 adds source PDF intake, per-document classification/extraction, deterministic normalization, and page-level provenance. Phase 3 adds deterministic, versioned documentary examination and a relational evidence graph. Phase 4 adds deterministic risk orchestration, synthetic provider signals and local cross-case duplicate search. Phase 5 adds deterministic recommendations, governed maker/checker approvals, specialist queues and a unified audit feed. Success is tracing each recommendation and human action to immutable source evidence and policy.

## Capabilities and Constraints

Dashboard KPIs and product distribution; searchable case register; case overview, parties, document inventory, trade lines, discrepancies, risk events, and historical approval events. Every supplied record is synthetic demo data. Expected PASS, REFER and BLOCK labels are supplied reference outcomes, separate from calculated system recommendations and governed human outcomes. Absent source fields remain empty. Phase 2 permits PDF upload, immutable versions, explicit processing/reprocessing, source page viewing, and extraction history. LLM calls receive source page text only; labels are evaluation-only. Insufficient native text requires review while endpoint vision support remains unverified. Phase 3 permits explicit documentary examination/reruns, immutable rule/fact snapshots, supported mismatch findings, current-fact inspection and evidence relations. Missing, ambiguous, unsupported or low-confidence inputs remain incomplete. Supplied reference findings/risks remain separate. Phase 4 permits explicit risk run/rerun/history, auditable provider outputs, versioned policies and calculated risk findings separate from references. Synthetic screening reference records simulate external providers; expected risk events and decisions remain evaluation-only. Missing price/country/goods references stay unchecked. Phase 5 permits explicit decision generation, demo-role actions, reviewed REFER exception acceptance and separate final human outcomes. Hard BLOCK, stale inputs and missing mandatory evidence cannot be waived. The optional Exception Resolution Agent drafts advice from existing reasons without decision authority. No OCR, live sanctions integration, payment execution or regulatory inference. LLM configuration remains backend-only.

## Brand Commitments

FinArth; Smart Trade. Polished, precise enterprise interface. User delegated visual design judgment and chose building directly in code. No supplied logo. Phase 5 preserves the operations ledger design established in DESIGN.md during Phase 1.

## Evidence on Hand

`data/raw/` includes the supplied matching XLSX and CSV datasets: 5 cases, 12 parties, 18 documents, 9 trade lines, 6 discrepancies, 6 risk events, 7 approval events, 14 passive rule references, 3 passive screening references. The committed data/demo/ source pack adds 18 original watermarked PDFs and five labelled case payloads, without duplicating the workbook. No invented business values or regulatory claims.

## Product Principles

- MySQL is the source of truth.
- Clearly distinguish supplied demo references from calculated results.
- Preserve source relationships and protect unrelated data.
- Keep operations readable, responsive, and keyboard accessible.
