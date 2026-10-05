"""Synchronous bounded processing with committed stages and explicit retry history."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.llm.client import LLMClient, LLMUnavailable
from app.integrations.pdf.parser import parse_pdf, persist_pages
from app.integrations.storage.local import InvalidDocument
from app.models.documents import DocumentProcessingRun, DocumentVersion
from app.models.domain import now
from app.schemas.intelligence import EXTRACTION_FIELDS
from app.services.document_classifier import (
    DOCUMENT_CLASSIFICATION_PROMPT_VERSION,
    classify_document,
    content_cue,
)
from app.services.document_extraction import (
    DOCUMENT_EXTRACTION_PROMPT_VERSION,
    extract_document,
    persist_raw_facts,
)
from app.services.documents import DocumentConflict, get_version, read_source
from app.services.evidence import normalize_and_validate

ACTIVE = {"PARSING", "PARSED", "CLASSIFYING", "EXTRACTING"}


def _stage(session, version, run, status, error=None, terminal=False, commit=True):
    run.status = version.status = status
    metadata = dict(run.metadata_json)
    metadata["stages"] = [*metadata.get("stages", []), {"status": status, "at": now().isoformat()}]
    run.metadata_json = metadata
    run.error_message = error
    if terminal:
        run.completed_at = now()
    if commit:
        session.commit()


def process_document(
    session: Session,
    settings: Settings,
    document_pk: int,
    force: bool = False,
    version_pk: int | None = None,
    client_factory=None,
) -> DocumentProcessingRun:
    version = get_version(session, document_pk, version_pk)
    # Serialize run creation across native workers; no long transaction around the LLM.
    version = session.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.id == version.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    previous = session.scalar(
        select(DocumentProcessingRun)
        .where(DocumentProcessingRun.document_version_pk == version.id)
        .order_by(DocumentProcessingRun.run_number.desc())
        .limit(1)
    )
    if previous and previous.status in ACTIVE:
        if previous.started_at > now() - timedelta(minutes=15):
            session.rollback()
            raise DocumentConflict("Document is already being processed")
        _stage(
            session,
            version,
            previous,
            "FAILED",
            "Interrupted processing run expired",
            True,
            commit=False,
        )
    if previous and previous.status == "COMPLETED" and not force:
        session.commit()
        return previous
    run = DocumentProcessingRun(
        document_version_pk=version.id,
        run_number=(previous.run_number + 1 if previous else 1),
        status="PARSING",
        llm_model=settings.llm_model,
        metadata_json={
            "classification_prompt": DOCUMENT_CLASSIFICATION_PROMPT_VERSION,
            "extraction_prompt": DOCUMENT_EXTRACTION_PROMPT_VERSION,
            "input": "source_pdf_pages_only",
            "vision": "unsupported_not_attempted",
        },
    )
    session.add(run)
    session.flush()
    run_id, version_id = run.id, version.id
    _stage(session, version, run, "PARSING")
    client = None
    try:
        parsed = parse_pdf(read_source(settings, version), settings.document_max_pages)
        persist_pages(session, version.id, parsed)
        version.page_count = len(parsed.pages)
        _stage(session, version, run, "PARSED")
        if parsed.needs_review:
            _stage(
                session,
                version,
                run,
                "NEEDS_REVIEW",
                "OCR_REQUIRED: insufficient native text; endpoint vision support is unverified",
                True,
            )
            return run
        if sum(len(p.text) for p in parsed.pages) > settings.document_max_text_chars:
            _stage(
                session,
                version,
                run,
                "NEEDS_REVIEW",
                "Document text exceeds the configured model input limit; no text was truncated",
                True,
            )
            return run
        _stage(session, version, run, "CLASSIFYING")
        client = (client_factory or LLMClient)(settings)
        classification = classify_document(client, parsed)
        run.document_type = classification.document_type
        run.classification_confidence = Decimal(str(classification.confidence))
        run.metadata_json = {
            **run.metadata_json,
            "classification": classification.model_dump(),
            "content_cue": content_cue(parsed),
        }
        if classification.document_type not in EXTRACTION_FIELDS:
            _stage(session, version, run, "NEEDS_REVIEW", "No supported extraction schema", True)
            return run
        _stage(session, version, run, "EXTRACTING")
        extracted = extract_document(client, parsed, classification.document_type)
        facts = persist_raw_facts(session, run, extracted, parsed)
        normalize_and_validate(facts, classification.document_type, parsed)
        review = (
            not facts
            or classification.confidence < 0.7
            or any(fact.evidence_status == "NEEDS_REVIEW" for fact in facts)
        )
        run.metadata_json = {
            **run.metadata_json,
            "fact_count": len(facts),
            "review_fact_count": sum(f.evidence_status == "NEEDS_REVIEW" for f in facts),
        }
        _stage(
            session,
            version,
            run,
            "NEEDS_REVIEW" if review else "COMPLETED",
            "Review extracted evidence or classification" if review else None,
            True,
        )
    except Exception as exc:
        session.rollback()
        run = session.get(DocumentProcessingRun, run_id)
        version = session.get(DocumentVersion, version_id)
        if isinstance(exc, (InvalidDocument, LLMUnavailable)):
            error = str(exc)
        else:
            error = "Document processing failed; internal details are suppressed"
        _stage(session, version, run, "FAILED", error, True)
    finally:
        if client:
            client.close()
    return run
