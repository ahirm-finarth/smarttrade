from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.pdf.parser import parse_pdf
from app.integrations.storage.local import (
    InvalidDocument,
    LocalSourceStorage,
    fingerprint,
    safe_filename,
    validate_upload,
)
from app.models.documents import DocumentVersion
from app.models.domain import CaseDocument, TradeCase
from app.services.cases import CaseNotFound


class DocumentNotFound(Exception):
    pass


class DocumentConflict(Exception):
    pass


def get_document(session: Session, document_pk: int) -> CaseDocument:
    document = session.get(CaseDocument, document_pk)
    if document is None:
        raise DocumentNotFound
    return document


def get_version(session: Session, document_pk: int, version_pk: int | None = None):
    get_document(session, document_pk)
    statement = select(DocumentVersion).where(DocumentVersion.document_pk == document_pk)
    if version_pk is not None:
        statement = statement.where(DocumentVersion.id == version_pk)
    version = session.scalar(statement.order_by(DocumentVersion.version_number.desc()).limit(1))
    if version is None:
        raise DocumentNotFound
    return version


def register_document(
    session: Session,
    settings: Settings,
    case_id: str,
    content: bytes,
    filename: str,
    mime_type: str | None = "application/pdf",
    document_pk: int | None = None,
):
    validate_upload(content, filename, mime_type, settings.document_max_bytes)
    parsed = parse_pdf(content, settings.document_max_pages)
    sha256 = fingerprint(content)
    case = session.scalar(select(TradeCase).where(TradeCase.case_id == case_id).with_for_update())
    if case is None:
        raise CaseNotFound
    duplicate = session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.case_pk == case.id, DocumentVersion.sha256 == sha256
        )
    )
    if duplicate:
        if document_pk is not None and document_pk != duplicate.document_pk:
            raise DocumentConflict(
                "Identical source already belongs to another document in this case"
            )
        session.commit()
        return duplicate, True
    if document_pk is None:
        document = CaseDocument(
            case_pk=case.id,
            source_key="upload:" + uuid4().hex,
            document_id="DOC-" + uuid4().hex,
            file_name=safe_filename(filename),
            received=True,
        )
        session.add(document)
        session.flush()
    else:
        document = session.scalar(
            select(CaseDocument)
            .where(CaseDocument.id == document_pk, CaseDocument.case_pk == case.id)
            .with_for_update()
        )
        if document is None:
            raise DocumentNotFound
    version_number = max((v.version_number for v in document.versions), default=0) + 1
    storage = LocalSourceStorage(settings.document_storage_root)
    key = None
    try:
        key = storage.save(content, case.id, document.id, version_number)
        version = DocumentVersion(
            document_pk=document.id,
            case_pk=case.id,
            version_number=version_number,
            original_filename=safe_filename(filename),
            storage_path=key,
            file_size_bytes=len(content),
            sha256=sha256,
            page_count=len(parsed.pages),
            status="UPLOADED",
        )
        session.add(version)
        session.commit()
        return version, False
    except Exception:
        session.rollback()
        if key:
            storage.remove(key)
        raise


def read_source(settings: Settings, version: DocumentVersion) -> bytes:
    try:
        content = LocalSourceStorage(settings.document_storage_root).read(version.storage_path)
    except OSError:
        raise InvalidDocument("Source file is unavailable in local storage") from None
    if fingerprint(content) != version.sha256:
        raise InvalidDocument("Source integrity check failed")
    return content
