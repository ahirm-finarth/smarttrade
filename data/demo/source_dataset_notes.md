# Smart Trade synthetic demo data

All files in this folder, the related `case_packets/` PDFs, and `case_payloads/` JSON payloads are **synthetic demo data only**. Do not use any record, party, instrument, identifier, document or screening signal to make a real operational, financial, legal, sanctions or regulatory decision.

## Quick start

1. Start with `trade_cases.csv` or the `Demo Dashboard` tab in `Smart_Trade_Demo_Data.xlsx`.
2. Open each case-specific JSON payload in `case_payloads/` to mock the Smart Trade case API.
3. Upload the PDFs under `case_packets/<case_id>/` to the document intake flow.
4. Reconcile the expected decision against `discrepancies.csv`, `risk_events.csv`, and `approval_events.csv`.

## Expected routes

- `ST-IMP-2026-0001`: Pass after maker/checker approval.
- `ST-IMP-2026-0002`: Refer; document, duplication, route and price controls require review.
- `ST-EXP-2026-0003`: Refer; late shipment and PO mismatch require a documented decision.
- `ST-COL-2026-0004`: Pass; acceptance and maturity monitoring workflow.
- `ST-BG-2026-0005`: Refer; the demand lacks a required breach statement.

## Files

- `case_parties.csv`: parties, roles and illustrative screening status.
- `case_documents.csv`: expected/reconciled documents and source packet filenames.
- `trade_lines.csv`: structured quantities and values used by consistency controls.
- `discrepancies.csv`: labelled expected exceptions and their evidence/route.
- `risk_events.csv`: labelled risk signals and expected decision treatment.
- `risk_rules.csv`: illustrative rules; substitute the bank-approved rulebook in implementation.
- `reference_screening.csv`: entirely fictional demo reference records, not a sanctions/PEP/watchlist source.
