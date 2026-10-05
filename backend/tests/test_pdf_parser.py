from pathlib import Path

import pymupdf
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.integrations.pdf.parser import parse_pdf, persist_pages
from app.integrations.storage.local import InvalidDocument
from app.models.documents import DocumentPage, DocumentVersion
from app.models.domain import Base, CaseDocument, TradeCase

PACKETS = Path(__file__).resolve().parents[2] / "data/demo/case_packets"


def test_every_fixture_is_native_and_watermarked():
    files = list(PACKETS.rglob("*.pdf"))
    assert len(files) == 18
    for file in files:
        parsed = parse_pdf(file.read_bytes())
        assert len(parsed.pages) == 1
        assert not parsed.needs_review
        assert "NOT A FINANCIAL INSTRUMENT" in parsed.pages[0].text


def test_bad_encrypted_and_text_poor_pdf():
    with pytest.raises(InvalidDocument):
        parse_pdf(b"%PDF-not-real")
    with pymupdf.open() as pdf:
        pdf.new_page()
        blank = pdf.tobytes()
        encrypted = pdf.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="test")
    assert parse_pdf(blank).needs_review
    with pytest.raises(InvalidDocument):
        parse_pdf(encrypted)
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.new_page()
        with pytest.raises(InvalidDocument):
            parse_pdf(pdf.tobytes(), max_pages=1)


def test_pages_are_persisted_and_reused():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        case = TradeCase(case_id="PDF-CASE")
        session.add(case)
        session.flush()
        doc = CaseDocument(case_pk=case.id, source_key="test")
        session.add(doc)
        session.flush()
        version = DocumentVersion(
            document_pk=doc.id,
            case_pk=case.id,
            version_number=1,
            original_filename="test.pdf",
            storage_path="test/source.pdf",
            file_size_bytes=1,
            sha256="a" * 64,
        )
        session.add(version)
        session.flush()
        parsed = parse_pdf(next(PACKETS.rglob("*.pdf")).read_bytes())
        persist_pages(session, version.id, parsed)
        persist_pages(session, version.id, parsed)
        assert len(list(session.scalars(select(DocumentPage)))) == 1
