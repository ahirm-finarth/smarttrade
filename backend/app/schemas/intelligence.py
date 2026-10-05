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
