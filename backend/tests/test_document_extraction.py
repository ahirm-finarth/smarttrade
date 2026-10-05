import pytest

from app.schemas.intelligence import EXTRACTION_FIELDS, extraction_schema


def response():
    return {
        "document_type": "COMMERCIAL_INVOICE",
        "fields": {
            "invoice_number": {
                "raw_value": "INV-1",
                "page": 1,
                "source_text": "Invoice reference\nINV-1",
                "confidence": 0.98,
            }
        },
    }


def test_document_specific_schemas():
    for kind in EXTRACTION_FIELDS:
        validated = extraction_schema(kind).model_validate(
            {"document_type": kind, "fields": {}}, strict=True
        )
        assert all(getattr(validated.fields, field) is None for field in EXTRACTION_FIELDS[kind])
    assert extraction_schema("COMMERCIAL_INVOICE").model_validate(response(), strict=True)
    with pytest.raises(ValueError):
        extraction_schema("OTHER")


@pytest.mark.parametrize(
    "change",
    [
        {"page": 0},
        {"page": "1"},
        {"confidence": 1.1},
        {"source_text": ""},
        {"raw_value": 100},
        {"normalized_value": "invented"},
    ],
)
def test_bad_evidence_is_rejected(change):
    payload = response()
    payload["fields"]["invoice_number"].update(change)
    with pytest.raises(ValueError):
        extraction_schema("COMMERCIAL_INVOICE").model_validate(payload, strict=True)


def test_wrong_type_and_unrequested_fields_rejected():
    payload = response()
    payload["fields"]["sanctions_result"] = payload["fields"]["invoice_number"]
    with pytest.raises(ValueError):
        extraction_schema("COMMERCIAL_INVOICE").model_validate(payload, strict=True)
    payload = response()
    payload["document_type"] = "PACKING_LIST"
    with pytest.raises(ValueError):
        extraction_schema("COMMERCIAL_INVOICE").model_validate(payload, strict=True)
