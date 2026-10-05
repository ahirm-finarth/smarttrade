# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

User-specified Next.js App Router, TypeScript, Tailwind CSS; Python 3.12+ FastAPI, Pydantic, SQLAlchemy, Alembic; externally supplied MySQL.

## Users

Trade operations users inspecting synthetic trade cases and their related records in an enterprise operations interface. Specific roles and production access requirements remain open for later phases.

## Product Purpose

FinArth Smart Trade is an evidence-led, governed trade-finance decision layer. Phase 1 establishes the persisted case inventory, dashboard, and read-only case workspace. Success is a source-grounded dashboard and inspectable cases fetched through the backend from MySQL.

## Capabilities and Constraints

Dashboard KPIs and product distribution; searchable case register; case overview, parties, document inventory, trade lines, discrepancies, risk events, and historical approval events. Every supplied record is synthetic demo data. PASS, REFER, and BLOCK are expected demo outcomes, never computed decisions. Absent source fields remain empty. No OCR, extraction, rule evaluation, sanctions integration, approval actions, or agent workflows in Phase 1. LLM configuration and client remain backend-only and opt-in.

## Brand Commitments

FinArth; Smart Trade. Polished, precise enterprise interface. User delegated visual design judgment and chose building directly in code. No supplied logo or established visual system.

## Evidence on Hand

`data/raw/` includes the supplied matching XLSX and CSV datasets: 5 cases, 12 parties, 18 documents, 9 trade lines, 6 discrepancies, 6 risk events, 7 approval events, 14 passive rule references, 3 passive screening references. No invented business values or regulatory claims.

## Product Principles

- MySQL is the source of truth.
- Clearly distinguish supplied demo references from calculated results.
- Preserve source relationships and protect unrelated data.
- Keep operations readable, responsive, and keyboard accessible.
