import json
import unicodedata

from app.integrations.pdf.parser import ParsedPDF
from app.models.documents import ExtractedFact
from app.schemas.intelligence import EXTRACTION_FIELDS
from app.services.normalization import NormalizationError, normalize_value


def canonical_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def reconcile_evidence(page_text: str, source_text: str, raw_value: str) -> bool:
    page, snippet, raw = map(canonical_text, (page_text, source_text, raw_value))
    return bool(snippet and raw and snippet in page and raw in snippet)


def normalize_and_validate(facts: list[ExtractedFact], document_type: str, parsed: ParsedPDF):
    pages = {page.page_number: page.text for page in parsed.pages}
    for fact in facts:
        reasons = []
        if not reconcile_evidence(
            pages.get(fact.page_number, ""), fact.source_text, fact.raw_value
        ):
            reasons.append("Source snippet or raw value could not be matched to the stored page")
        if fact.confidence < 0.65:
            reasons.append("Extraction confidence is below the review threshold")
        try:
            normalized = normalize_value(
                EXTRACTION_FIELDS[document_type][fact.field_name], fact.raw_value
            )
            fact.normalized_json = normalized
            fact.normalized_value = (
                normalized
                if isinstance(normalized, str)
                else json.dumps(normalized, ensure_ascii=False, sort_keys=True)
            )
        except NormalizationError as exc:
            reasons.append(str(exc))
            fact.normalized_json = None
            fact.normalized_value = None
        fact.evidence_status = "NEEDS_REVIEW" if reasons else "SUPPORTED"
        fact.review_reason = "; ".join(reasons)[:255] if reasons else None
