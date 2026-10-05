"""Batch-load only current Phase 2 source evidence. Never consult reference findings."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.documents import DocumentProcessingRun, DocumentVersion
from app.models.domain import CaseDocument, TradeCase
from app.rules import Subject
from app.services.cases import CaseNotFound
from app.services.evidence import reconcile_evidence

ELIGIBLE_RUNS = {"COMPLETED", "NEEDS_REVIEW"}


def load_case_evidence(session: Session, case: TradeCase) -> dict:
    documents = session.scalars(
        select(CaseDocument)
        .where(CaseDocument.case_pk == case.id)
        .order_by(CaseDocument.id)
        .options(
            selectinload(CaseDocument.versions).selectinload(DocumentVersion.pages),
            selectinload(CaseDocument.versions)
            .selectinload(DocumentVersion.runs)
            .selectinload(DocumentProcessingRun.facts),
        )
        .execution_options(populate_existing=True)
    ).all()
    return build_case_evidence(case, documents)


def build_case_evidence(case: TradeCase, documents: list[CaseDocument]) -> dict:
    result = {
        "case_id": case.case_id,
        "case_pk": case.id,
        "playbook": case.product_playbook,
        "documents": [],
    }
    for document in documents:
        version, run = document.latest_version, document.latest_run
        if not version:
            result["documents"].append(
                {
                    "document_id": document.id,
                    "document_type": None,
                    "status": "NOT_REGISTERED",
                    "facts": [],
                }
            )
            continue
        pages = {page.page_number: page for page in version.pages}
        item = {
            "document_id": document.id,
            "document_version_id": version.id,
            "version_number": version.version_number,
            "filename": version.original_filename,
            "sha256": version.sha256,
            "processing_run_id": run.id if run else None,
            "processing_run_number": run.run_number if run else None,
            "document_type": run.document_type if run else None,
            "status": run.status if run else version.status,
            "classification_confidence": str(run.classification_confidence)
            if run and run.classification_confidence is not None
            else None,
            "page_count": version.page_count,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text_content": p.text_content,
                    "needs_review": p.needs_review,
                }
                for p in sorted(pages.values(), key=lambda p: p.page_number)
            ],
            "facts": [],
        }
        if run:
            for fact in sorted(run.facts, key=lambda f: f.id):
                page = pages.get(fact.page_number)
                supported = bool(
                    page
                    and not page.needs_review
                    and reconcile_evidence(page.text_content, fact.source_text, fact.raw_value)
                )
                item["facts"].append(
                    {
                        "fact_id": fact.id,
                        "case_id": case.case_id,
                        "document_id": document.id,
                        "document_version_id": version.id,
                        "version_number": version.version_number,
                        "processing_run_id": run.id,
                        "processing_run_number": run.run_number,
                        "filename": version.original_filename,
                        "document_type": run.document_type,
                        "field_name": fact.field_name,
                        "raw_value": fact.raw_value,
                        "normalized_value": fact.normalized_json,
                        "comparison_value": fact.normalized_json,
                        "page_number": fact.page_number,
                        "source_text": fact.source_text,
                        "confidence": str(fact.confidence),
                        "evidence_status": fact.evidence_status,
                        "source_verified": supported,
                        "review_reason": fact.review_reason,
                    }
                )
        result["documents"].append(item)
    return result


def case_by_id(session: Session, case_id: str) -> TradeCase:
    case = session.scalar(select(TradeCase).where(TradeCase.case_id == case_id))
    if case is None:
        raise CaseNotFound
    return case


@dataclass(frozen=True)
class Resolution:
    state: str
    reason: str
    evidence: dict | None = None
    candidate_fact_ids: tuple[int, ...] = ()

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "reason": self.reason,
            "evidence": self.evidence,
            "candidate_fact_ids": list(self.candidate_fact_ids),
        }


def resolve(corpus: dict, subject: Subject, threshold: Decimal) -> Resolution:
    documents = [d for d in corpus["documents"] if d["document_type"] == subject.document_type]
    if not documents:
        return Resolution("MISSING", "No current classified source document for this role")
    if len(documents) != 1:
        return Resolution(
            "NEEDS_REVIEW",
            "Multiple current documents compete for a scalar role; no arbitrary selection",
        )
    document = documents[0]
    if document["status"] not in ELIGIBLE_RUNS:
        return Resolution(
            "NEEDS_REVIEW",
            "Latest source version/run is not ready; older evidence was not substituted",
        )
    confidence = document["classification_confidence"]
    if confidence is None or Decimal(confidence) < threshold:
        return Resolution(
            "NEEDS_REVIEW", "Document classification is below the examination confidence threshold"
        )
    if subject.fields == ("@document",):
        pages = document["pages"]
        if not pages or any(p["needs_review"] for p in pages):
            return Resolution("NEEDS_REVIEW", "Document presence lacks readable source evidence")
        page = pages[0]
        evidence = {
            k: v
            for k, v in document.items()
            if k not in {"facts", "pages", "sha256", "status", "classification_confidence"}
        }
        evidence.update(
            {
                "case_id": corpus["case_id"],
                "fact_id": None,
                "field_name": "@document",
                "raw_value": "Present",
                "normalized_value": True,
                "comparison_value": True,
                "page_number": page["page_number"],
                "source_text": page["text_content"],
                "confidence": confidence,
                "evidence_status": "SUPPORTED",
                "source_verified": True,
                "role": subject.role,
            }
        )
        return Resolution(
            "READY", "Configured demo presence backed by the classified original", evidence
        )
    # Alternatives are explicit role aliases, tried in priority order within one source run.
    selected = None
    for field in subject.fields:
        candidate = [f for f in document["facts"] if f["field_name"] == field]
        if len(candidate) > 1:
            return Resolution(
                "NEEDS_REVIEW",
                "Multiple facts compete for this field",
                candidate_fact_ids=tuple(f["fact_id"] for f in candidate),
            )
        if candidate:
            selected = candidate[0]
            break
    if selected is None:
        return Resolution("MISSING", "Required field was not extracted from the latest source run")
    evidence = {**selected, "role": subject.role}
    if (
        evidence["evidence_status"] != "SUPPORTED"
        or not evidence["source_verified"]
        or Decimal(evidence["confidence"]) < threshold
    ):
        return Resolution(
            "NEEDS_REVIEW", "Fact confidence or source support is insufficient", evidence
        )
    if evidence["normalized_value"] is None:
        return Resolution("NOT_COMPARABLE", "Fact has no valid normalized value", evidence)
    if subject.route_part and evidence["field_name"] == "route":
        value = evidence["normalized_value"]
        parts = value.split("/") if isinstance(value, str) else []
        if len(parts) != 2 or not all(p.strip() for p in parts):
            return Resolution(
                "NOT_COMPARABLE", "Route does not provide exactly two ordered ports", evidence
            )
        evidence["comparison_value"] = parts[0 if subject.route_part == "loading" else 1].strip()
        evidence["derivation"] = (
            f"Ordered loading/discharge route: {subject.route_part} part; original route retained"
        )
    return Resolution("READY", "Unique current source-backed fact", evidence)
