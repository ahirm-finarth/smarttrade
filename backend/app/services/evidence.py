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


def anchor_native_evidence(fact: ExtractedFact, page_text: str, kind: str) -> dict | None:
    """Reconcile a label-only model quote to its unique adjacent native value.

    Never infer text. For formatted money/date/quantity, accept only deterministic
    normalization equality and preserve the model's original representation in run metadata.
    """
    if reconcile_evidence(page_text, fact.source_text, fact.raw_value):
        return None
    lines = page_text.splitlines(keepends=True)
    matches = [
        i
        for i, line in enumerate(lines[:-1])
        if canonical_text(line) == canonical_text(fact.source_text)
    ]
    if len(matches) != 1:
        return None
    index = matches[0]
    native_value = lines[index + 1].strip()
    quote = lines[index] + lines[index + 1]
    raw = fact.raw_value
    if canonical_text(raw) not in canonical_text(native_value):
        if kind not in {"money", "date", "quantity"}:
            return None
        try:
            if normalize_value(kind, raw) != normalize_value(kind, native_value):
                return None
        except NormalizationError:
            return None
        raw = native_value
    if not reconcile_evidence(page_text, quote, raw):
        return None
    original = {
        "model_raw_value": fact.raw_value,
        "model_source_text": fact.source_text,
        "method": "unique_adjacent_native_row",
    }
    fact.raw_value, fact.source_text = raw, quote.rstrip("\r\n")
    return original


def normalize_and_validate(facts: list[ExtractedFact], document_type: str, parsed: ParsedPDF):
    pages = {page.page_number: page.text for page in parsed.pages}
    reconciliations = {}
    for fact in facts:
        kind = EXTRACTION_FIELDS[document_type][fact.field_name]
        original = anchor_native_evidence(fact, pages.get(fact.page_number, ""), kind)
        if original:
            reconciliations[fact.field_name] = original
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

    return reconciliations
