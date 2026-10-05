import argparse
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.documents import DocumentVersion
from app.models.domain import CaseDocument, TradeCase
from app.services.demo_documents import PACKETS
from app.services.document_processing import process_document


def main():
    parser = argparse.ArgumentParser(
        description="Explicitly process registered synthetic source PDFs"
    )
    parser.add_argument("--case-id")
    parser.add_argument("--reprocess", action="store_true")
    args = parser.parse_args()
    engine, settings = get_engine(), get_settings()
    counts = Counter()
    files = {(path.parent.name, path.name) for path in PACKETS.glob("*/*.pdf")}
    with Session(engine) as session:
        rows = session.execute(
            select(
                DocumentVersion.id,
                CaseDocument.id,
                TradeCase.case_id,
                DocumentVersion.original_filename,
                DocumentVersion.status,
            )
            .join(CaseDocument, CaseDocument.id == DocumentVersion.document_pk)
            .join(TradeCase, TradeCase.id == CaseDocument.case_pk)
            .order_by(TradeCase.case_id, CaseDocument.id, DocumentVersion.version_number)
        ).all()
    for version_id, document_id, case_id, filename, status in rows:
        if (case_id, filename) not in files or (args.case_id and case_id != args.case_id):
            continue
        if status in {"COMPLETED", "NEEDS_REVIEW"} and not args.reprocess:
            counts[status] += 1
            print(f"{case_id} / {filename}: {status} (existing)", flush=True)
            continue
        try:
            with Session(engine) as session:
                run = process_document(
                    session, settings, document_id, force=args.reprocess, version_pk=version_id
                )
                counts[run.status] += 1
                print(f"{case_id} / {filename}: {run.status} ({len(run.facts)} facts)", flush=True)
        except Exception:
            counts["FAILED"] += 1
            print(f"{case_id} / {filename}: FAILED (details suppressed)", flush=True)
    print("Processing results:", dict(counts), flush=True)
    if counts["FAILED"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
