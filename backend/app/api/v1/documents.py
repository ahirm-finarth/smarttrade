from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.models.domain import TradeCase
from app.schemas.cases import Document
from app.schemas.documents import (
    DocumentDetail,
    Fact,
    Page,
    ProcessingRun,
    UploadResult,
    Version,
)
from app.services.demo_import import DATASET_KEY
from app.services.document_processing import process_document
from app.services.documents import get_document, get_version, read_source, register_document

router = APIRouter(prefix="/api/v1")
Database = Annotated[Session, Depends(get_session)]


@router.post("/cases/{case_id}/documents", response_model=UploadResult)
def upload_document(
    case_id: str,
    session: Database,
    file: Annotated[UploadFile, File()],
    document_id: Annotated[int | None, Form()] = None,
):
    settings = get_settings()
    content = file.file.read(settings.document_max_bytes + 1)
    version, duplicate = register_document(
        session,
        settings,
        case_id,
        content,
        file.filename or "document.pdf",
        file.content_type,
        document_id,
    )
    return UploadResult(
        document_id=version.document_pk,
        version=Version.model_validate(version),
        duplicate=duplicate,
    )


def document_detail(session, document_id, version_id=None, run_id=None):
    document = get_document(session, document_id)
    case = session.get(TradeCase, document.case_pk)
    version = get_version(session, document_id, version_id) if document.versions else None
    runs = sorted((r for v in document.versions for r in v.runs), key=lambda r: r.id, reverse=True)
    selected_run = None
    if version:
        selected_run = max(version.runs, key=lambda r: r.run_number, default=None)
    if run_id:
        selected_run = next((r for r in runs if r.id == run_id), None)
        if not selected_run:
            raise HTTPException(404, "Processing run not found for this document")
        version = get_version(session, document_id, selected_run.document_version_pk)
    return DocumentDetail(
        document=Document.model_validate(document),
        case_id=case.case_id,
        is_synthetic=case.dataset_key == DATASET_KEY,
        versions=[
            Version.model_validate(v)
            for v in sorted(document.versions, key=lambda v: v.version_number, reverse=True)
        ],
        selected_version=Version.model_validate(version) if version else None,
        pages=[Page.model_validate(p) for p in sorted(version.pages, key=lambda p: p.page_number)]
        if version
        else [],
        processing_runs=[ProcessingRun.model_validate(r) for r in runs],
        selected_run=ProcessingRun.model_validate(selected_run) if selected_run else None,
        facts=[Fact.model_validate(f) for f in sorted(selected_run.facts, key=lambda f: f.id)]
        if selected_run
        else [],
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def detail(
    document_id: int,
    session: Database,
    version_id: int | None = Query(None, ge=1),
    run_id: int | None = Query(None, ge=1),
):
    return document_detail(session, document_id, version_id, run_id)


@router.post("/documents/{document_id}/process", response_model=ProcessingRun)
def process(document_id: int, session: Database, version_id: int | None = Query(None, ge=1)):
    return process_document(session, get_settings(), document_id, version_pk=version_id)


@router.post("/documents/{document_id}/reprocess", response_model=ProcessingRun)
def reprocess(document_id: int, session: Database, version_id: int | None = Query(None, ge=1)):
    return process_document(session, get_settings(), document_id, force=True, version_pk=version_id)


@router.get("/documents/{document_id}/processing-runs", response_model=list[ProcessingRun])
def runs(document_id: int, session: Database):
    return document_detail(session, document_id).processing_runs


@router.get("/documents/{document_id}/facts", response_model=list[Fact])
def facts(document_id: int, session: Database, run_id: int | None = Query(None, ge=1)):
    return document_detail(session, document_id, run_id=run_id).facts


@router.get("/documents/{document_id}/source")
def source(document_id: int, session: Database, version_id: int | None = Query(None, ge=1)):
    version = get_version(session, document_id, version_id)
    content = read_source(get_settings(), version)
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename*=UTF-8''" + quote(version.original_filename),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
