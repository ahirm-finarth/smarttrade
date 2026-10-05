"""Versioned, inspectable configuration selecting preimplemented comparisons."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.intelligence import EXTRACTION_FIELDS
from app.services.comparisons import ComparisonType, decimal_value

RULESET_VERSION = "documentary-v1"
IMPORT = "Import LC"
EXPORT = "Export LC"
COLLECTION = "Documentary Collection D/A"
GUARANTEE = "Performance Guarantee"
PLAYBOOKS = (IMPORT, EXPORT, COLLECTION, GUARANTEE)


class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_type: str
    fields: tuple[str, ...] = Field(min_length=1)
    role: str
    route_part: Literal["loading", "discharge"] | None = None

    @model_validator(mode="after")
    def valid_fields(self):
        available = EXTRACTION_FIELDS.get(self.document_type)
        if not available or any(f != "@document" and f not in available for f in self.fields):
            raise ValueError("Unknown document type or extraction field")
        if "@document" in self.fields and self.fields != ("@document",):
            raise ValueError("Presence cannot be mixed with extracted values")
        if self.route_part and "route" not in self.fields:
            raise ValueError("Route derivation requires a route source field")
        return self


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^DOC-[A-Z0-9-]+$", max_length=64)
    version: int = Field(default=1, ge=1)
    playbooks: tuple[str, ...] = Field(min_length=1)
    name: str
    left: Subject
    right: Subject
    comparison: ComparisonType
    severity: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    finding_type: str
    relation_type: Literal["GOVERNS", "COMPARED_WITH", "SUPPORTS"] = "GOVERNS"
    parameters: dict[str, str | tuple[str, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_config(self):
        if any(p not in PLAYBOOKS for p in self.playbooks):
            raise ValueError("Unknown playbook")
        presence = self.comparison == ComparisonType.DOCUMENT_PRESENT
        if presence != (self.left.fields == ("@document",) and self.right.fields == ("@document",)):
            raise ValueError("Document presence requires document subjects")
        permitted = {
            ComparisonType.AMOUNT_WITHIN_TOLERANCE: {"tolerance_percent", "mode"},
            ComparisonType.CONTAINS_REQUIRED_TEXT: {"required_text", "aliases"},
        }.get(self.comparison, set())
        if set(self.parameters) - permitted:
            raise ValueError("Unsupported comparison parameters")
        if self.comparison == ComparisonType.AMOUNT_WITHIN_TOLERANCE:
            if set(self.parameters) != {"tolerance_percent", "mode"}:
                raise ValueError("Amount tolerance and direction must be explicit")
            if decimal_value(self.parameters["tolerance_percent"]) > Decimal("100"):
                raise ValueError("Unsupported tolerance")
            if self.parameters["mode"] not in {"equal", "at_most"}:
                raise ValueError("Unknown amount policy")
        if self.comparison == ComparisonType.CONTAINS_REQUIRED_TEXT:
            if (
                not isinstance(self.parameters.get("required_text"), str)
                or not self.parameters["required_text"].strip()
            ):
                raise ValueError("Required text must be explicit")
        return self


def subject(document, field, role, *, fallback=(), route_part=None):
    return Subject(
        document_type=document, fields=(field, *fallback), role=role, route_part=route_part
    )


def rule(id, playbooks, name, left, right, comparison, finding_type, **kwargs):
    return Rule(
        id=id,
        playbooks=playbooks,
        name=name,
        left=left,
        right=right,
        comparison=comparison,
        finding_type=finding_type,
        **kwargs,
    )


LC, INV, PACK, BL, COO = (
    "LETTER_OF_CREDIT",
    "COMMERCIAL_INVOICE",
    "PACKING_LIST",
    "BILL_OF_LADING",
    "CERTIFICATE_OF_ORIGIN",
)
COL, BOE, BG, DEMAND, CONTRACT = (
    "COLLECTION_INSTRUCTION",
    "BILL_OF_EXCHANGE",
    "BANK_GUARANTEE",
    "GUARANTEE_DEMAND",
    "CONTRACT_EXTRACT",
)
LC_PRODUCTS = (IMPORT, EXPORT)
STRICT_AMOUNT = {"tolerance_percent": "0", "mode": "equal"}

RULES = [
    rule(
        "DOC-LC-CURRENCY-001",
        LC_PRODUCTS,
        "LC and invoice currency",
        subject(LC, "amount", "LC currency"),
        subject(INV, "total_amount", "Invoice currency"),
        "CURRENCY_EQUAL",
        "CURRENCY_MISMATCH",
    ),
    rule(
        "DOC-LC-AMOUNT-001",
        LC_PRODUCTS,
        "Invoice amount against LC amount",
        subject(LC, "amount", "Governing credit amount"),
        subject(INV, "total_amount", "Presented invoice amount"),
        "AMOUNT_WITHIN_TOLERANCE",
        "AMOUNT_MISMATCH",
        parameters=STRICT_AMOUNT,
    ),
    rule(
        "DOC-LC-SELLER-001",
        LC_PRODUCTS,
        "LC beneficiary and invoice seller",
        subject(LC, "beneficiary", "Expected seller", fallback=("exporter",)),
        subject(INV, "seller", "Invoice seller"),
        "PARTY_NAME_MATCH",
        "SELLER_MISMATCH",
    ),
    rule(
        "DOC-LC-GOODS-001",
        LC_PRODUCTS,
        "LC and invoice goods",
        subject(LC, "goods_description", "Governing goods"),
        subject(INV, "goods_description", "Invoice goods"),
        "NORMALIZED_TEXT",
        "GOODS_MISMATCH",
        severity="MEDIUM",
    ),
    rule(
        "DOC-LC-QTY-001",
        LC_PRODUCTS,
        "LC and invoice quantity",
        subject(LC, "quantity", "Governing quantity"),
        subject(INV, "quantity", "Invoice quantity"),
        "QUANTITY_EQUAL",
        "QUANTITY_MISMATCH",
    ),
    rule(
        "DOC-LC-SHIP-001",
        LC_PRODUCTS,
        "Shipment against LC deadline",
        subject(LC, "latest_shipment_date", "Latest shipment deadline"),
        subject(BL, "shipment_date", "On-board shipment date"),
        "DATE_ON_OR_BEFORE",
        "LATE_SHIPMENT",
    ),
    rule(
        "DOC-IMP-BUYER-001",
        (IMPORT,),
        "LC applicant and invoice buyer",
        subject(LC, "applicant", "Expected buyer"),
        subject(INV, "buyer", "Invoice buyer"),
        "PARTY_NAME_MATCH",
        "BUYER_MISMATCH",
    ),
    rule(
        "DOC-IMP-PACK-QTY-001",
        (IMPORT,),
        "LC and packing-list quantity",
        subject(LC, "quantity", "Governing quantity"),
        subject(PACK, "quantity", "Packed quantity"),
        "QUANTITY_EQUAL",
        "QUANTITY_MISMATCH",
    ),
    rule(
        "DOC-IMP-INV-PACK-QTY-001",
        (IMPORT,),
        "Invoice and packed quantity",
        subject(INV, "quantity", "Invoice quantity"),
        subject(PACK, "quantity", "Packed quantity"),
        "QUANTITY_EQUAL",
        "PACKED_QUANTITY_MISMATCH",
        relation_type="COMPARED_WITH",
    ),
    rule(
        "DOC-IMP-INV-PACK-REF-001",
        (IMPORT,),
        "Packing-list invoice reference",
        subject(INV, "invoice_number", "Invoice identifier"),
        subject(PACK, "invoice_number", "Packing-list invoice reference"),
        "NORMALIZED_IDENTIFIER",
        "INVOICE_REFERENCE_MISMATCH",
        severity="MEDIUM",
        relation_type="COMPARED_WITH",
    ),
    rule(
        "DOC-IMP-LOAD-001",
        (IMPORT,),
        "LC and transport loading port",
        subject(
            LC,
            "port_of_loading",
            "Expected loading port",
            fallback=("route",),
            route_part="loading",
        ),
        subject(BL, "port_of_loading", "Transport loading port"),
        "PORT_MATCH",
        "LOADING_PORT_MISMATCH",
        severity="MEDIUM",
    ),
    rule(
        "DOC-IMP-DISCHARGE-001",
        (IMPORT,),
        "LC and transport discharge port",
        subject(
            LC,
            "port_of_discharge",
            "Expected discharge port",
            fallback=("route",),
            route_part="discharge",
        ),
        subject(BL, "port_of_discharge", "Transport discharge port"),
        "PORT_MATCH",
        "DISCHARGE_PORT_MISMATCH",
        severity="MEDIUM",
    ),
    rule(
        "DOC-IMP-CONSIGNEE-001",
        (IMPORT,),
        "LC applicant and transport consignee",
        subject(LC, "applicant", "Expected consignee"),
        subject(BL, "consignee", "Transport consignee"),
        "PARTY_NAME_MATCH",
        "CONSIGNEE_MISMATCH",
    ),
    rule(
        "DOC-EXP-BUYER-001",
        (EXPORT,),
        "Export LC and invoice buyer",
        subject(LC, "buyer", "Expected buyer"),
        subject(INV, "buyer", "Invoice buyer"),
        "PARTY_NAME_MATCH",
        "BUYER_MISMATCH",
    ),
    rule(
        "DOC-EXP-PO-001",
        (EXPORT,),
        "LC and invoice purchase order",
        subject(LC, "purchase_order_reference", "Governing purchase order"),
        subject(INV, "purchase_order_reference", "Invoice purchase order"),
        "NORMALIZED_IDENTIFIER",
        "PURCHASE_ORDER_MISMATCH",
        severity="MEDIUM",
    ),
    rule(
        "DOC-EXP-CONSIGNEE-001",
        (EXPORT,),
        "Export buyer and transport consignee",
        subject(LC, "buyer", "Expected consignee"),
        subject(BL, "consignee", "Transport consignee"),
        "PARTY_NAME_MATCH",
        "CONSIGNEE_MISMATCH",
    ),
    rule(
        "DOC-EXP-ORIGIN-EXPORTER-001",
        (EXPORT,),
        "Invoice seller and origin exporter",
        subject(INV, "seller", "Invoice seller"),
        subject(COO, "exporter", "Origin certificate exporter"),
        "PARTY_NAME_MATCH",
        "ORIGIN_EXPORTER_MISMATCH",
        relation_type="SUPPORTS",
    ),
    rule(
        "DOC-EXP-ORIGIN-GOODS-001",
        (EXPORT,),
        "Invoice and certificate goods",
        subject(INV, "goods_description", "Invoice goods"),
        subject(COO, "goods_description", "Origin certificate goods"),
        "NORMALIZED_TEXT",
        "ORIGIN_GOODS_MISMATCH",
        severity="MEDIUM",
        relation_type="SUPPORTS",
    ),
]

for target, suffix in ((INV, "INV"), (PACK, "PACK"), (BL, "BL")):
    products = LC_PRODUCTS if target in (INV, BL) else (IMPORT,)
    RULES.append(
        rule(
            f"DOC-LC-PRESENCE-{suffix}-001",
            products,
            f"Configured {target.lower().replace('_', ' ')} presence",
            subject(LC, "@document", "Governing LC document"),
            subject(target, "@document", "Required demonstration document"),
            "DOCUMENT_PRESENT",
            "DOCUMENT_MISSING",
        )
    )
RULES.append(
    rule(
        "DOC-EXP-PRESENCE-COO-001",
        (EXPORT,),
        "Configured origin certificate presence",
        subject(LC, "@document", "Governing LC document"),
        subject(COO, "@document", "Required demonstration certificate"),
        "DOCUMENT_PRESENT",
        "DOCUMENT_MISSING",
    )
)

for target, prefix, amount_field in ((INV, "INV", "total_amount"), (BOE, "BOE", "amount")):
    for suffix, field, other, comparison, finding in (
        ("CURRENCY", "amount", amount_field, "CURRENCY_EQUAL", "CURRENCY_MISMATCH"),
        ("AMOUNT", "amount", amount_field, "AMOUNT_WITHIN_TOLERANCE", "COLLECTION_AMOUNT_MISMATCH"),
        (
            "DRAWER",
            "drawer",
            "seller" if target == INV else "drawer",
            "PARTY_NAME_MATCH",
            "COLLECTION_DRAWER_MISMATCH",
        ),
        (
            "DRAWEE",
            "drawee",
            "buyer" if target == INV else "drawee",
            "PARTY_NAME_MATCH",
            "COLLECTION_DRAWEE_MISMATCH",
        ),
        ("PRESENCE", "@document", "@document", "DOCUMENT_PRESENT", "DOCUMENT_MISSING"),
    ):
        RULES.append(
            rule(
                f"DOC-COL-{prefix}-{suffix}-001",
                (COLLECTION,),
                f"Collection instruction against {prefix} {suffix.lower()}",
                subject(COL, field, f"Instruction {field}"),
                subject(target, other, f"Presented {other}"),
                comparison,
                finding,
                parameters=STRICT_AMOUNT if comparison == "AMOUNT_WITHIN_TOLERANCE" else {},
            )
        )

RULES.extend(
    [
        rule(
            "DOC-BG-CURRENCY-001",
            (GUARANTEE,),
            "Guarantee and demand currency",
            subject(BG, "amount", "Guarantee currency"),
            subject(DEMAND, "demand_amount", "Demand currency"),
            "CURRENCY_EQUAL",
            "CURRENCY_MISMATCH",
        ),
        rule(
            "DOC-BG-AMOUNT-001",
            (GUARANTEE,),
            "Demand within guarantee amount",
            subject(BG, "amount", "Guaranteed amount"),
            subject(DEMAND, "demand_amount", "Demand amount"),
            "AMOUNT_WITHIN_TOLERANCE",
            "DEMAND_AMOUNT_EXCEEDED",
            parameters={"tolerance_percent": "0", "mode": "at_most"},
        ),
        rule(
            "DOC-BG-BENEFICIARY-001",
            (GUARANTEE,),
            "Guarantee and demand beneficiary",
            subject(BG, "beneficiary", "Guarantee beneficiary"),
            subject(DEMAND, "beneficiary", "Demand beneficiary"),
            "PARTY_NAME_MATCH",
            "DEMAND_BENEFICIARY_MISMATCH",
        ),
        rule(
            "DOC-BG-EXPIRY-001",
            (GUARANTEE,),
            "Demand presentation before expiry",
            subject(BG, "expiry_date", "Guarantee expiry"),
            subject(DEMAND, "demand_date", "Demand presentation"),
            "DATE_ON_OR_BEFORE",
            "DEMAND_AFTER_EXPIRY",
        ),
        rule(
            "DOC-BG-STATEMENT-001",
            (GUARANTEE,),
            "Explicit required breach statement",
            subject(BG, "required_demand_conditions", "Governing demand condition"),
            subject(
                DEMAND,
                "breach_statement",
                "Demand statement or explicit absence notice",
                fallback=("notice",),
            ),
            "CONTAINS_REQUIRED_TEXT",
            "REQUIRED_BREACH_STATEMENT_MISSING",
            parameters={"required_text": "statement of breach", "aliases": ("breach statement",)},
        ),
        rule(
            "DOC-BG-CONTRACTOR-001",
            (GUARANTEE,),
            "Guarantee applicant and contract contractor",
            subject(BG, "applicant", "Guarantee applicant"),
            subject(CONTRACT, "contractor", "Contract contractor"),
            "PARTY_NAME_MATCH",
            "CONTRACTOR_MISMATCH",
            relation_type="SUPPORTS",
        ),
        rule(
            "DOC-BG-EMPLOYER-001",
            (GUARANTEE,),
            "Guarantee beneficiary and contract employer",
            subject(BG, "beneficiary", "Guarantee beneficiary"),
            subject(CONTRACT, "employer", "Contract employer"),
            "PARTY_NAME_MATCH",
            "EMPLOYER_MISMATCH",
            relation_type="SUPPORTS",
        ),
    ]
)
for target, suffix in ((DEMAND, "DEMAND"), (CONTRACT, "CONTRACT")):
    RULES.append(
        rule(
            f"DOC-BG-PRESENCE-{suffix}-001",
            (GUARANTEE,),
            f"Configured {suffix.lower()} presence",
            subject(BG, "@document", "Governing guarantee document"),
            subject(target, "@document", "Required demonstration document"),
            "DOCUMENT_PRESENT",
            "DOCUMENT_MISSING",
        )
    )


def validate_rules(rules: list[Rule]) -> tuple[Rule, ...]:
    if len({r.id for r in rules}) != len(rules):
        raise ValueError("Duplicate rule IDs")
    return tuple(rules)


def load_rules(playbook: str) -> tuple[Rule, ...]:
    if playbook not in PLAYBOOKS:
        raise ValueError("No documentary examination playbook is configured")
    return tuple(r for r in validate_rules(RULES) if playbook in r.playbooks)
