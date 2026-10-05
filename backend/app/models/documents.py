"""Versioned originals and append-only processing evidence (no trade decisions)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain import PK, TABLE_OPTIONS, Base, UTCDateTime, now

PAGE_TEXT = Text().with_variant(LONGTEXT(), "mysql")


class DocumentVersion(Base):
    __tablename__ = "smart_trade_document_versions"
    __table_args__ = (
        UniqueConstraint("document_pk", "version_number"),
        UniqueConstraint("case_pk", "sha256"),
        TABLE_OPTIONS,
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    document_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_case_documents.id"), index=True
    )
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(64), default="application/pdf")
    file_size_bytes: Mapped[int] = mapped_column(PK)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED")
    page_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now, onupdate=now)
    pages: Mapped[list["DocumentPage"]] = relationship(cascade="all, delete-orphan")
    runs: Mapped[list["DocumentProcessingRun"]] = relationship(cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "smart_trade_document_pages"
    __table_args__ = (UniqueConstraint("document_version_pk", "page_number"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    document_version_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_document_versions.id"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    text_content: Mapped[str] = mapped_column(PAGE_TEXT)
    text_length: Mapped[int] = mapped_column(Integer)
    extraction_method: Mapped[str] = mapped_column(String(32), default="NATIVE_TEXT")
    needs_review: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class DocumentProcessingRun(Base):
    __tablename__ = "smart_trade_document_processing_runs"
    __table_args__ = (UniqueConstraint("document_version_pk", "run_number"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    document_version_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_document_versions.id"), index=True
    )
    run_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    parser: Mapped[str] = mapped_column(String(64), default="PyMuPDF/native-v1")
    llm_model: Mapped[str | None] = mapped_column(String(255))
    document_type: Mapped[str | None] = mapped_column(String(64))
    classification_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    facts: Mapped[list["ExtractedFact"]] = relationship(cascade="all, delete-orphan")


class ExtractedFact(Base):
    __tablename__ = "smart_trade_extracted_facts"
    __table_args__ = (UniqueConstraint("processing_run_pk", "field_name"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    processing_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_document_processing_runs.id"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(100))
    raw_value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    normalized_json: Mapped[Any | None] = mapped_column(JSON)
    page_number: Mapped[int] = mapped_column(Integer)
    source_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    evidence_status: Mapped[str] = mapped_column(String(32), default="NEEDS_REVIEW")
    review_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
