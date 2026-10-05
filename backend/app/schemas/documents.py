from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.schemas.cases import Document, ReadModel


class Version(ReadModel):
    id: int
    document_pk: int
    version_number: int
    original_filename: str
    mime_type: str
    file_size_bytes: int
    sha256: str
    status: str
    page_count: int | None
    created_at: datetime
    updated_at: datetime


class Page(ReadModel):
    id: int
    page_number: int
    text_content: str
    text_length: int
    extraction_method: str
    needs_review: bool


class ProcessingRun(ReadModel):
    id: int
    document_version_pk: int
    run_number: int
    status: str
    parser: str
    llm_model: str | None
    document_type: str | None
    classification_confidence: Decimal | None
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    metadata_json: dict[str, Any]


class Fact(ReadModel):
    document_id: int | None = None
    document_version_id: int | None = None
    case_id: str | None = None
    document_type: str | None = None
    id: int
    processing_run_pk: int
    field_name: str
    raw_value: str
    normalized_value: str | None
    normalized_json: Any | None
    page_number: int
    source_text: str
    confidence: Decimal
    evidence_status: str
    review_reason: str | None
    created_at: datetime


class DocumentDetail(BaseModel):
    document: Document
    case_id: str
    is_synthetic: bool
    versions: list[Version]
    selected_version: Version | None
    pages: list[Page]
    processing_runs: list[ProcessingRun]
    selected_run: ProcessingRun | None
    facts: list[Fact]


class UploadResult(BaseModel):
    document_id: int
    version: Version
    duplicate: bool
