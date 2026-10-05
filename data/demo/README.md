# Synthetic document fixtures

Every PDF is **SYNTHETIC DEMO — NOT A FINANCIAL INSTRUMENT**. These fictional fixtures are for development and evaluation only. Preserve all visible source markings.

- `case_packets/`: 18 original, one-page PDFs in five case folders.
- `case_payloads/`: five labelled JSON case references, for evaluation only.
- `demo_manifest.json`: original supplier manifest. Some items listed there were not supplied; this repository does not invent them.
- `source_dataset_notes.md`: original notes for the supplied datasets.

The nine CSV datasets and `Smart_Trade_Demo_Data.xlsx` already live in [`../raw/`](../raw/). Their copies in this pack were byte-identical and are deliberately not duplicated. Phase 1 seed paths remain compatible. The original manifest describes the supplier's layout rather than this deduplicated layout.

Document processing reads only source PDFs. CSV, XLSX, and JSON labels are never extraction inputs. Runtime copies and uploaded PDFs belong in ignored `storage/`, not here. Registration and processing are separate commands; see the project README.
