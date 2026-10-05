# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

User-specified Next.js App Router, TypeScript, Tailwind CSS; Python 3.12+ FastAPI, Pydantic, SQLAlchemy, Alembic; externally supplied MySQL.

## Users

Trade operations users inspecting synthetic trade cases and their related records in an enterprise operations interface. Specific roles and production access requirements remain open for later phases.

## Product Purpose

FinArth Smart Trade is an evidence-led, governed trade-finance decision layer. Phase 1 establishes the persisted case inventory and dashboard. Phase 2 adds source PDF intake, per-document classification/extraction, deterministic normalization, and page-level provenance. Phase 3 adds deterministic, versioned documentary examination and a relational evidence graph. Success is comparing actual extracted facts and tracing each result to its two original source pages.

## Capabilities and Constraints

Dashboard KPIs and product distribution; searchable case register; case overview, parties, document inventory, trade lines, discrepancies, risk events, and historical approval events. Every supplied record is synthetic demo data. PASS, REFER, and BLOCK are expected demo outcomes, never computed decisions. Absent source fields remain empty. Phase 2 permits PDF upload, immutable versions, explicit processing/reprocessing, source page viewing, and extraction history. LLM calls receive source page text only; labels are evaluation-only. Insufficient native text requires review while endpoint vision support remains unverified. Phase 3 permits explicit documentary examination/reruns, immutable rule/fact snapshots, supported mismatch findings, current-fact inspection and evidence relations. Missing, ambiguous, unsupported or low-confidence inputs remain incomplete. Supplied reference findings/risks remain separate. No OCR, sanctions integration, approval actions, final computed decisions, risk orchestration or regulatory inference. LLM configuration remains backend-only.

## Brand Commitments

FinArth; Smart Trade. Polished, precise enterprise interface. User delegated visual design judgment and chose building directly in code. No supplied logo. Phase 3 preserves the operations ledger design established in DESIGN.md during Phase 1.

## Evidence on Hand

`data/raw/` includes the supplied matching XLSX and CSV datasets: 5 cases, 12 parties, 18 documents, 9 trade lines, 6 discrepancies, 6 risk events, 7 approval events, 14 passive rule references, 3 passive screening references. The committed data/demo/ source pack adds 18 original watermarked PDFs and five labelled case payloads, without duplicating the workbook. No invented business values or regulatory claims.

## Product Principles

- MySQL is the source of truth.
- Clearly distinguish supplied demo references from calculated results.
- Preserve source relationships and protect unrelated data.
- Keep operations readable, responsive, and keyboard accessible.
