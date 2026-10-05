from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.session import get_session
from app.integrations.llm.client import LLMUnavailable
from app.main import app
from app.models.documents import DocumentProcessingRun, DocumentVersion, ExtractedFact
from app.models.domain import Base, CaseDocument, TradeCase
from app.services.document_processing import process_document
from app.services.documents import DocumentConflict, register_document

PDF = Path(__file__).resolve().parents[2] / (
    "data/demo/case_packets/ST-IMP-2026-0001/Commercial_Invoice_INV-NT-260101.pdf"
)


class MockLLM:
    def __init__(self, settings):
        pass

    def structured(self, messages, schema, max_tokens):
        source = messages[1]["content"]
        assert "INV-NT-260101" in source
        assert "expected_decision" not in source
        if schema.__name__ == "Classification":
            payload = {
                "document_type": "COMMERCIAL_INVOICE",
                "confidence": 0.99,
                "reason": "Commercial invoice heading",
            }
        else:
            payload = {
                "document_type": "COMMERCIAL_INVOICE",
                "fields": {
                    "invoice_number": {
                        "raw_value": "INV-NT-260101",
                        "page": 1,
                        "source_text": "Invoice reference\nINV-NT-260101",
                        "confidence": 0.99,
                    },
                    "total_amount": {
                        "raw_value": "USD 85,000",
                        "page": 1,
                        "source_text": "Invoice amount\nUSD 85,000",
                        "confidence": 0.98,
                    },
                },
            }
        return schema.model_validate(payload, strict=True)

    def close(self):
        pass


@pytest.fixture()
def context(tmp_path):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, document_storage_root=tmp_path / "storage")
    with Session(engine) as session:
        session.add_all([TradeCase(case_id="TEST-1"), TradeCase(case_id="TEST-2")])
        session.commit()
    yield engine, settings
    engine.dispose()


def test_duplicate_versions_reprocess_and_provenance(context):
    engine, settings = context
    with Session(engine) as session:
        version, duplicate = register_document(
            session, settings, "TEST-1", PDF.read_bytes(), PDF.name
        )
        assert not duplicate
        duplicate_version, duplicate = register_document(
            session, settings, "TEST-1", PDF.read_bytes(), PDF.name
        )
        assert duplicate and duplicate_version.id == version.id
        assert session.scalar(select(func.count()).select_from(CaseDocument)) == 1
        run = process_document(session, settings, version.document_pk, client_factory=MockLLM)
        assert run.status == "COMPLETED"
        assert run.facts[1].normalized_json == {"currency": "USD", "amount": "85000.00"}
        assert all(f.evidence_status == "SUPPORTED" for f in run.facts)
        assert run.document_version_pk == version.id
        assert run.metadata_json["input"] == "source_pdf_pages_only"
        assert [s["status"] for s in run.metadata_json["stages"]] == [
            "PARSING",
            "PARSED",
            "CLASSIFYING",
            "EXTRACTING",
            "COMPLETED",
        ]
        assert (
            process_document(session, settings, version.document_pk, client_factory=MockLLM).id
            == run.id
        )
        new_run = process_document(
            session, settings, version.document_pk, force=True, client_factory=MockLLM
        )
        assert new_run.run_number == 2 and new_run.id != run.id
        assert session.scalar(select(func.count()).select_from(ExtractedFact)) == 4
        with pymupdf.open(PDF) as pdf:
            pdf.set_metadata({"title": "second immutable source version"})
            second = pdf.tobytes()
        second_version, _ = register_document(
            session, settings, "TEST-1", second, PDF.name, document_pk=version.document_pk
        )
        assert second_version.version_number == 2
        assert version.sha256 != second_version.sha256
        assert session.scalar(select(func.count()).select_from(DocumentVersion)) == 2
        assert len(run.facts) == 2
        other_case, _ = register_document(session, settings, "TEST-2", PDF.read_bytes(), PDF.name)
        assert other_case.case_pk != version.case_pk


def test_failure_is_persisted_and_retriable(context):
    engine, settings = context

    class FailedLLM(MockLLM):
        def structured(self, *args, **kwargs):
            raise LLMUnavailable("Model output failed structured schema validation")

    with Session(engine) as session:
        version, _ = register_document(session, settings, "TEST-1", PDF.read_bytes(), PDF.name)
        failed = process_document(session, settings, version.document_pk, client_factory=FailedLLM)
        assert failed.status == "FAILED" and failed.completed_at
        assert not failed.facts
        recovered = process_document(session, settings, version.document_pk, client_factory=MockLLM)
        assert recovered.run_number == 2 and recovered.status == "COMPLETED"
        assert session.get(DocumentProcessingRun, failed.id).status == "FAILED"


def test_blank_source_requires_review_without_llm(context):
    engine, settings = context
    with pymupdf.open() as pdf:
        pdf.new_page()
        blank = pdf.tobytes()

    def no_llm(_):
        raise AssertionError("Text-poor source must not invoke an unverified vision model")

    with Session(engine) as session:
        version, _ = register_document(session, settings, "TEST-1", blank, "blank.pdf")
        run = process_document(session, settings, version.document_pk, client_factory=no_llm)
        assert run.status == "NEEDS_REVIEW" and "OCR_REQUIRED" in run.error_message
        assert not run.facts


def test_active_run_prevents_overlap(context):
    engine, settings = context
    with Session(engine) as session:
        version, _ = register_document(session, settings, "TEST-1", PDF.read_bytes(), PDF.name)
        session.add(
            DocumentProcessingRun(
                document_version_pk=version.id, run_number=1, status="EXTRACTING", metadata_json={}
            )
        )
        session.commit()
        with pytest.raises(DocumentConflict):
            process_document(
                session, settings, version.document_pk, force=True, client_factory=MockLLM
            )


def test_document_api_end_to_end(context, monkeypatch):
    engine, settings = context
    monkeypatch.setattr("app.api.v1.documents.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.document_processing.LLMClient", MockLLM)

    def database():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = database
    try:
        with TestClient(app) as client:
            file = {"file": (PDF.name, PDF.read_bytes(), "application/pdf")}
            uploaded = client.post("/api/v1/cases/TEST-1/documents", files=file)
            assert uploaded.status_code == 200
            doc_id = uploaded.json()["document_id"]
            duplicate = client.post("/api/v1/cases/TEST-1/documents", files=file)
            assert duplicate.json()["duplicate"]
            prefix = f"/api/v1/documents/{doc_id}"
            assert client.get(prefix).json()["selected_version"]["status"] == "UPLOADED"
            assert "storage_path" not in client.get(prefix).text
            assert client.get(prefix + "/source").content == PDF.read_bytes()
            assert client.post(prefix + "/process").json()["status"] == "COMPLETED"
            assert len(client.get(prefix + "/facts").json()) == 2
            assert client.post(prefix + "/reprocess").json()["run_number"] == 2
            assert len(client.get(prefix + "/processing-runs").json()) == 2
            detail = client.get(prefix).json()
            assert detail["facts"][0]["page_number"] == 1
            assert detail["pages"][0]["text_length"] > 100
            assert client.get(prefix, params={"version_id": 999}).status_code == 404
            assert client.get(prefix + "/facts", params={"run_id": 999}).status_code == 404
            assert client.get("/api/v1/documents/999").status_code == 404
            assert client.post("/api/v1/cases/UNKNOWN/documents", files=file).status_code == 404
            assert (
                client.post(
                    "/api/v1/cases/TEST-1/documents",
                    files={"file": ("bad.pdf", b"%PDF-invalid", "application/pdf")},
                ).status_code
                == 422
            )
    finally:
        app.dependency_overrides.clear()


def test_bad_source_quotes_get_one_bounded_repair_attempt(context):
    engine, settings = context

    class RepairLLM(MockLLM):
        attempts = 0

        def structured(self, messages, schema, max_tokens):
            result = super().structured(messages, schema, max_tokens)
            if schema.__name__ != "Classification":
                self.attempts += 1
                if self.attempts == 1:
                    result.fields.invoice_number.source_text = "Invoice reference"
                else:
                    assert "Validation feedback" in messages[1]["content"]
            return result

    with Session(engine) as session:
        version, _ = register_document(session, settings, "TEST-1", PDF.read_bytes(), PDF.name)
        run = process_document(session, settings, version.document_pk, client_factory=RepairLLM)
        assert run.status == "COMPLETED"
        assert run.metadata_json["extraction_attempts"] == 2
        assert all(f.evidence_status == "SUPPORTED" for f in run.facts)
        assert len(run.facts) == 2
