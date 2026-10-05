# Supplied synthetic demo sources

`raw/` contains the original Smart Trade workbook and nine CSV files from the supplied synthetic demo pack. The CSVs and workbook have matching data. Default import uses CSVs; `--source data/raw/Smart_Trade_Demo_Data.xlsx` explicitly uses the workbook.

Expected source counts: trade cases 5; parties 12; documents 18; trade lines 9; discrepancies 6; risk events 6; approval events 7; passive risk rules 14; passive screening references 3.

The case source has no customer ID, facility ID, priority, or case timestamps. Those business fields remain NULL. `created_at` and `updated_at` track persistence time, not invented trade events. Source approval timestamps include offsets and are normalized to UTC.

Document extraction confidence, screening statuses, findings, risk results, approval events, and expected outcomes are source-provided synthetic references. No extraction, rule execution, screening, approval action, or decision calculation occurs.

The importer validates source schemas and numeric precision, rejects orphan relationships and duplicate source identifiers, and commits atomically. Existing non-demo identifiers are protected. Case business IDs and stable related identifiers prevent duplicates; only `demo:`-owned related rows for the supplied demo cases are reconciled. Omitted datasets and unrelated records are preserved. Cases omitted from a later source are preserved rather than deleted automatically.

Document PDFs and case packets are outside Phase 1; the UI displays the supplied inventory metadata only.
