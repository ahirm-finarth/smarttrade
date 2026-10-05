from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    LETTER_OF_CREDIT = "LETTER_OF_CREDIT"
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    PACKING_LIST = "PACKING_LIST"
    BILL_OF_LADING = "BILL_OF_LADING"
    CERTIFICATE_OF_ORIGIN = "CERTIFICATE_OF_ORIGIN"
    BILL_OF_EXCHANGE = "BILL_OF_EXCHANGE"
    COLLECTION_INSTRUCTION = "COLLECTION_INSTRUCTION"
    BANK_GUARANTEE = "BANK_GUARANTEE"
    GUARANTEE_DEMAND = "GUARANTEE_DEMAND"
    CONTRACT_EXTRACT = "CONTRACT_EXTRACT"
    OTHER = "OTHER"


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Classification(StrictOutput):
    # Literal-like enumeration remains JSON-strict without requiring Python Enum instances.
    document_type: str = Field(pattern="^(" + "|".join(DocumentType) + ")$")
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=300)


class FieldEvidence(StrictOutput):
    raw_value: str = Field(min_length=1, max_length=4000)
    page: int = Field(ge=1)
    source_text: str = Field(min_length=1, max_length=8000)
    confidence: float = Field(ge=0, le=1)


# Narrow schemas reflect the actual supplied document classes. Absent values stay null.
EXTRACTION_FIELDS: dict[str, dict[str, str]] = {
    "LETTER_OF_CREDIT": {
        "lc_number": "text",
        "applicant": "text",
        "beneficiary": "text",
        "exporter": "text",
        "buyer": "text",
        "amount": "money",
        "goods_description": "text",
        "quantity": "quantity",
        "latest_shipment_date": "date",
        "port_of_loading": "text",
        "port_of_discharge": "text",
        "route": "text",
        "purchase_order_reference": "text",
    },
    "COMMERCIAL_INVOICE": {
        "invoice_number": "text",
        "seller": "text",
        "buyer": "text",
        "goods_description": "text",
        "quantity": "quantity",
        "unit_price": "money",
        "total_amount": "money",
        "purchase_order_reference": "text",
    },
    "PACKING_LIST": {
        "document_number": "text",
        "invoice_number": "text",
        "goods_description": "text",
        "quantity": "quantity",
        "packages": "quantity",
    },
    "BILL_OF_LADING": {
        "bl_number": "text",
        "vessel_name": "text",
        "shipment_date": "date",
        "port_of_loading": "text",
        "port_of_discharge": "text",
        "consignee": "text",
    },
    "CERTIFICATE_OF_ORIGIN": {
        "certificate_number": "text",
        "exporter": "text",
        "goods_description": "text",
        "country_of_origin": "text",
    },
    "BILL_OF_EXCHANGE": {
        "bill_number": "text",
        "drawer": "text",
        "drawee": "text",
        "amount": "money",
        "tenor": "text",
    },
    "COLLECTION_INSTRUCTION": {
        "collection_reference": "text",
        "drawer": "text",
        "drawee": "text",
        "collection_type": "text",
        "amount": "money",
        "maturity_date": "date",
        "release_condition": "text",
    },
    "BANK_GUARANTEE": {
        "guarantee_number": "text",
        "applicant": "text",
        "beneficiary": "text",
        "amount": "money",
        "expiry_date": "date",
        "required_demand_conditions": "text",
    },
    "GUARANTEE_DEMAND": {
        "demand_reference": "text",
        "beneficiary": "text",
        "demand_amount": "money",
        "demand_date": "date",
        "notice": "text",
        "breach_statement": "text",
    },
    "CONTRACT_EXTRACT": {
        "contract_reference": "text",
        "project": "text",
        "contractor": "text",
        "employer": "text",
    },
}


def extraction_schema(document_type: str) -> type[StrictOutput]:
    from typing import Literal

    from pydantic import create_model

    if document_type not in EXTRACTION_FIELDS:
        raise ValueError("No extraction schema for this document type")
    fields = create_model(
        document_type + "Fields",
        __base__=StrictOutput,
        **{name: (FieldEvidence | None, None) for name in EXTRACTION_FIELDS[document_type]},
    )
    return create_model(
        document_type + "Extraction",
        __base__=StrictOutput,
        document_type=(Literal[document_type], ...),
        fields=(fields, ...),
    )
