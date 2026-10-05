from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.documents import DocumentProcessingRun, DocumentVersion
from app.models.domain import Base, CaseDocument
from app.services.demo_documents import register_demo_documents
from app.services.demo_evaluation import evaluate_demo_extraction
from app.services.demo_import import ingest, read_sources
from tests.test_import import RAW


def test_demo_registration_is_idempotent_and_does_not_process(tmp_path):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, document_storage_root=tmp_path)
    with Session(engine) as session:
        ingest(session, read_sources(RAW))
        session.commit()
        before = list(session.scalars(select(CaseDocument.id).order_by(CaseDocument.id)))
        assert register_demo_documents(session, settings) == {
            "registered": 18,
            "already_registered": 0,
        }
        assert register_demo_documents(session, settings) == {
            "registered": 0,
            "already_registered": 18,
        }
        assert list(session.scalars(select(CaseDocument.id).order_by(CaseDocument.id))) == before
        assert session.scalar(select(func.count()).select_from(DocumentVersion)) == 18
        assert session.scalar(select(func.count()).select_from(DocumentProcessingRun)) == 0
        # Re-seeding Phase 1 must preserve registered document IDs and source versions.
        ingest(session, read_sources(RAW))
        session.commit()
        assert register_demo_documents(session, settings)["already_registered"] == 18
        evaluation = evaluate_demo_extraction(session)
        assert evaluation["registered_pdfs"] == 18
        assert evaluation["processed_pdfs"] == 0
        assert evaluation["successfully_processed_pdfs"] == 0
        assert evaluation["metrics"]["classification"] == {"correct": 0, "labelled": 18}
        assert evaluation["metrics"]["money"]["labelled"] == 8
        assert evaluation["metrics"]["quantity"]["labelled"] == 8
        assert "No document-date ground truth" in evaluation["skipped"]["dates"]
    engine.dispose()
