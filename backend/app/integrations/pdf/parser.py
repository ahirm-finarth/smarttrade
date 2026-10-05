"""Page-aware native extraction. No OCR or inferred page text."""

from dataclasses import dataclass

import pymupdf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.storage.local import InvalidDocument
from app.models.documents import DocumentPage


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str
    needs_review: bool


@dataclass(frozen=True)
class ParsedPDF:
    pages: list[ParsedPage]

    @property
    def needs_review(self):
        return any(page.needs_review for page in self.pages)


def parse_pdf(content: bytes, max_pages: int = 100) -> ParsedPDF:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            if pdf.needs_pass or pdf.page_count < 1 or pdf.page_count > max_pages:
                raise InvalidDocument("PDF is encrypted, empty, or exceeds the page limit")
            if pdf.is_repaired:
                raise InvalidDocument("PDF is damaged and required repair")
            pages = []
            for number, page in enumerate(pdf, start=1):
                text = page.get_text("text", sort=False).replace("\x00", "")
                useful = sum(character.isalnum() for character in text)
                pages.append(ParsedPage(number, text, useful < 80 or len(text.split()) < 12))
            return ParsedPDF(pages)
    except InvalidDocument:
        raise
    except Exception:
        raise InvalidDocument("PDF could not be safely parsed") from None


def persist_pages(session: Session, version_pk: int, parsed: ParsedPDF):
    """Originals are immutable, so reprocessing reuses the first stored native text."""
    existing = list(
        session.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_version_pk == version_pk)
            .order_by(DocumentPage.page_number)
        )
    )
    if existing:
        if [(p.page_number, p.text_content) for p in existing] != [
            (p.page_number, p.text) for p in parsed.pages
        ]:
            raise InvalidDocument("Stored page text differs from the immutable source")
        return existing
    pages = [
        DocumentPage(
            document_version_pk=version_pk,
            page_number=p.page_number,
            text_content=p.text,
            text_length=len(p.text),
            needs_review=p.needs_review,
        )
        for p in parsed.pages
    ]
    session.add_all(pages)
    session.flush()
    return pages
