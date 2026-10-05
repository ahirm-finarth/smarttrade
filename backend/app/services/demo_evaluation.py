"""Development-only labelled reference comparison; never imported by AI services."""

import csv
from collections import Counter
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ROOT
from app.models.domain import CaseDocument, TradeCase
from app.services.evidence import canonical_text

LABEL_TYPES = {
    "LC advice": ("LETTER_OF_CREDIT", "lc_number", "LC"),
    "Export LC": ("LETTER_OF_CREDIT", "lc_number", "LC"),
    "Commercial invoice": ("COMMERCIAL_INVOICE", "invoice_number", "Invoice"),
    "Packing list": ("PACKING_LIST", "document_number", "Packing list"),
    "Bill of lading": ("BILL_OF_LADING", "bl_number", None),
    "Certificate of origin": ("CERTIFICATE_OF_ORIGIN", "certificate_number", None),
    "Bill of exchange": ("BILL_OF_EXCHANGE", "bill_number", None),
    "Collection instruction": ("COLLECTION_INSTRUCTION", "collection_reference", None),
    "Guarantee summary": ("BANK_GUARANTEE", "guarantee_number", "Guarantee"),
    "Demand letter": ("GUARANTEE_DEMAND", "demand_reference", None),
    "Underlying contract extract": ("CONTRACT_EXTRACT", "contract_reference", None),
}


def evaluate_demo_extraction(session: Session, source: Path = ROOT / "data/raw"):
    def read(name):
        with (source / (name + ".csv")).open(encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    labels, lines = read("case_documents"), read("trade_lines")
    metrics = {
        name: {"correct": 0, "labelled": 0}
        for name in ("classification", "reference", "money", "quantity", "goods_description")
    }
    statuses, kinds = Counter(), Counter()
    results = []
    processed = registered = 0

    def compare(name, correct, row_results):
        metrics[name]["labelled"] += 1
        metrics[name]["correct"] += int(correct)
        row_results[name] = bool(correct)

    for label in labels:
        document = session.scalar(
            select(CaseDocument)
            .join(TradeCase)
            .where(
                TradeCase.case_id == label["case_id"], CaseDocument.file_name == label["file_name"]
            )
        )
        version = document.latest_version if document else None
        run = document.latest_run if document else None
        registered += bool(version)
        processed += bool(run and run.completed_at)
        statuses[run.status if run else "NOT_PROCESSED"] += 1
        kinds[run.document_type if run and run.document_type else "UNCLASSIFIED"] += 1
        expected_type, reference_field, line_source = LABEL_TYPES[label["document_type"]]
        facts = (
            {f.field_name: f for f in run.facts if f.evidence_status == "SUPPORTED"} if run else {}
        )
        row_results = {"case_id": label["case_id"], "filename": label["file_name"]}
        compare("classification", bool(run and run.document_type == expected_type), row_results)
        reference = facts.get(reference_field)
        compare(
            "reference",
            bool(
                reference
                and canonical_text(reference.raw_value) == canonical_text(label["reference"])
            ),
            row_results,
        )
        matched_lines = [
            line
            for line in lines
            if line["case_id"] == label["case_id"] and line["source"] == line_source
        ]
        # Only a single explicitly mapped labelled trade line is covered by these scalar schemas.
        if len(matched_lines) == 1:
            line = matched_lines[0]
            if expected_type in {"LETTER_OF_CREDIT", "COMMERCIAL_INVOICE", "BANK_GUARANTEE"}:
                field = "total_amount" if expected_type == "COMMERCIAL_INVOICE" else "amount"
                money = facts.get(field)
                value = money.normalized_json if money else None
                correct = isinstance(value, dict) and value.get("currency") == line["currency"]
                if correct:
                    correct = Decimal(value.get("amount", "NaN")) == Decimal(line["line_amount"])
                compare("money", bool(correct), row_results)
            if expected_type in {"LETTER_OF_CREDIT", "COMMERCIAL_INVOICE", "PACKING_LIST"}:
                quantity = facts.get("quantity")
                value = quantity.normalized_json if quantity else None
                correct = isinstance(value, dict) and value.get("unit") == line["uom"].upper()
                if correct:
                    correct = Decimal(value.get("quantity", "NaN")) == Decimal(line["quantity"])
                compare("quantity", bool(correct), row_results)
                goods = facts.get("goods_description")
                compare(
                    "goods_description",
                    bool(
                        goods
                        and canonical_text(goods.raw_value)
                        == canonical_text(line["goods_description"])
                    ),
                    row_results,
                )
        results.append(row_results)
    return {
        "scope": "Labelled development fixtures only; not trade compliance checks",
        "registered_pdfs": registered,
        "processed_pdfs": processed,
        "statuses": dict(statuses),
        "classification_types": dict(kinds),
        "metrics": metrics,
        "skipped": {
            "dates": "No document-date ground truth in supplied reference datasets",
            "other_fields": "No unambiguous document-specific labels; not scored",
            "multi_line": "Scalar extraction only; multi-line items not scored",
        },
        "documents": results,
    }
