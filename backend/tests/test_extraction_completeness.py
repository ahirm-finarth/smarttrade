from app.integrations.pdf.parser import ParsedPage, ParsedPDF
from app.schemas.intelligence import extraction_schema
from app.services.document_extraction import printed_field_omissions


def test_printed_field_feedback_never_manufactures_a_fact():
    schema = extraction_schema("BILL_OF_LADING")
    output = schema.model_validate({"document_type": "BILL_OF_LADING", "fields": {}})
    pdf = ParsedPDF([ParsedPage(1, "On-board date\n2026-04-17\nVessel\nMV Example", False)])
    assert printed_field_omissions(output, pdf) == ["vessel_name", "shipment_date"]
    assert output.fields.shipment_date is None
    assert printed_field_omissions(output, ParsedPDF([ParsedPage(1, "No date", False)])) == []
    ambiguous = ParsedPDF([*pdf.pages, *pdf.pages])
    assert printed_field_omissions(output, ambiguous) == []


def test_absence_notice_is_distinct_from_breach_statement():
    schema = extraction_schema("GUARANTEE_DEMAND")
    output = schema.model_validate({"document_type": "GUARANTEE_DEMAND", "fields": {}})
    pdf = ParsedPDF([ParsedPage(1, "Notice\nRequired breach statement absent", False)])
    assert printed_field_omissions(output, pdf) == ["notice"]
    assert output.fields.breach_statement is None
