"""Fixture registration maps filenames to inventory; labels never enter processing."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ROOT, Settings
from app.models.domain import CaseDocument, TradeCase
from app.services.documents import DocumentConflict, register_document

PACKETS = ROOT / "data/demo/case_packets"


def register_demo_documents(session: Session, settings: Settings, packets: Path = PACKETS):
    counts = {"registered": 0, "already_registered": 0}
    for path in sorted(packets.glob("*/*.pdf")):
        case_id = path.parent.name
        matches = list(
            session.scalars(
                select(CaseDocument)
                .join(TradeCase)
                .where(TradeCase.case_id == case_id, CaseDocument.file_name == path.name)
            )
        )
        if len(matches) > 1:
            raise DocumentConflict("Ambiguous demo document inventory")
        _, duplicate = register_document(
            session,
            settings,
            case_id,
            path.read_bytes(),
            path.name,
            document_pk=matches[0].id if matches else None,
        )
        counts["already_registered" if duplicate else "registered"] += 1
    return counts
