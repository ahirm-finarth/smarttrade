"""Small deterministic comparison library; no LLM, floats, or reference datasets."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Any


class ComparisonType(StrEnum):
    NORMALIZED_TEXT = "NORMALIZED_TEXT"
    NORMALIZED_IDENTIFIER = "NORMALIZED_IDENTIFIER"
    PARTY_NAME_MATCH = "PARTY_NAME_MATCH"
    PORT_MATCH = "PORT_MATCH"
    CURRENCY_EQUAL = "CURRENCY_EQUAL"
    AMOUNT_WITHIN_TOLERANCE = "AMOUNT_WITHIN_TOLERANCE"
    QUANTITY_EQUAL = "QUANTITY_EQUAL"
    DATE_ON_OR_BEFORE = "DATE_ON_OR_BEFORE"
    CONTAINS_REQUIRED_TEXT = "CONTAINS_REQUIRED_TEXT"
    DOCUMENT_PRESENT = "DOCUMENT_PRESENT"


class ComparisonStatus(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING_LEFT = "MISSING_LEFT"
    MISSING_RIGHT = "MISSING_RIGHT"
    MISSING_BOTH = "MISSING_BOTH"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass(frozen=True)
class ComparisonResult:
    status: ComparisonStatus
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


def normalized_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A nonempty text value is required")
    text = unicodedata.normalize("NFKC", value).translate(
        str.maketrans({"’": "'", "‘": "'", "–": "-", "—": "-"})
    )
    return " ".join(text.casefold().split())


def normalized_identifier(value: str) -> str:
    # Preserve token boundaries, slashes, punctuation and leading zeroes.
    return re.sub(r"[-\s]+", "-", normalized_text(value))


def normalized_party(value: str) -> str:
    tokens = normalized_text(value).split()
    aliases = {"pvt": "private", "ltd": "limited", "corp": "corporation", "co": "company"}
    for index in range(max(0, len(tokens) - 3), len(tokens)):
        token = tokens[index].rstrip(".,")
        if token in aliases or token in aliases.values():
            tokens[index] = aliases.get(token, token)
    return " ".join(tokens)


def decimal_value(value: Any) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d+)?", value):
        raise ValueError("A normalized nonnegative Decimal string is required")
    try:
        number = Decimal(value)
        if not number.is_finite() or len(number.as_tuple().digits) > 20:
            raise ValueError("Unsupported numeric precision")
        return number
    except InvalidOperation:
        raise ValueError("Invalid Decimal") from None


def currency(value: Any) -> str:
    if not isinstance(value, dict) or not re.fullmatch(r"[A-Z]{3}", value.get("currency", "")):
        raise ValueError("A normalized currency is required")
    return value["currency"]


def _result(equal: bool, reason: str, **details) -> ComparisonResult:
    return ComparisonResult(
        ComparisonStatus.MATCH if equal else ComparisonStatus.MISMATCH, reason, details
    )


def _required_text(left: str, right: str, parameters: dict) -> ComparisonResult:
    expected, observed = normalized_text(left), normalized_text(right)
    phrases = [normalized_text(parameters["required_text"])]
    phrases.extend(normalized_text(p) for p in parameters.get("aliases", []))
    if not any(p in expected for p in phrases):
        return ComparisonResult(
            ComparisonStatus.NOT_COMPARABLE, "Governing fact does not establish this requirement"
        )
    negative = r"(?:no|without|not required|not provided|missing|absent)"
    for phrase in phrases:
        escaped = re.escape(phrase)
        if re.search(rf"{negative}.{{0,30}}{escaped}|{escaped}.{{0,30}}{negative}", expected):
            return ComparisonResult(
                ComparisonStatus.NOT_COMPARABLE, "Governing requirement is negated or ambiguous"
            )
        if re.search(rf"{negative}.{{0,30}}{escaped}|{escaped}.{{0,30}}{negative}", observed):
            return ComparisonResult(
                ComparisonStatus.MISMATCH,
                "Observed source explicitly states the required statement is absent",
                {"required_text": parameters["required_text"], "explicit_absence": True},
            )
    if parameters.get("observed_field") == "breach_statement":
        return ComparisonResult(
            ComparisonStatus.MATCH, "A supported explicit statement was extracted from the demand"
        )
    return ComparisonResult(
        ComparisonStatus.NOT_COMPARABLE,
        "A notice mentioning a statement does not establish a submitted statement",
    )


def compare(kind: str, left: Any, right: Any, parameters: dict | None = None) -> ComparisonResult:
    parameters = parameters or {}
    if left is None or right is None:
        status = (
            ComparisonStatus.MISSING_BOTH
            if left is None and right is None
            else ComparisonStatus.MISSING_LEFT
            if left is None
            else ComparisonStatus.MISSING_RIGHT
        )
        return ComparisonResult(status, "Required extracted input is missing")
    try:
        comparison = ComparisonType(kind)
        if comparison in {ComparisonType.NORMALIZED_TEXT, ComparisonType.PORT_MATCH}:
            a, b = normalized_text(left), normalized_text(right)
            return _result(a == b, "Conservative normalized text comparison", left=a, right=b)
        if comparison == ComparisonType.NORMALIZED_IDENTIFIER:
            a, b = normalized_identifier(left), normalized_identifier(right)
            return _result(a == b, "Identifier token boundaries retained", left=a, right=b)
        if comparison == ComparisonType.PARTY_NAME_MATCH:
            a, b = normalized_party(left), normalized_party(right)
            if a != b and SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.88:
                return ComparisonResult(
                    ComparisonStatus.NEEDS_REVIEW,
                    "Similar party names differ beyond controlled suffix aliases",
                    {"left": a, "right": b},
                )
            return _result(a == b, "Controlled party suffix normalization", left=a, right=b)
        if comparison == ComparisonType.CURRENCY_EQUAL:
            a, b = currency(left), currency(right)
            return _result(a == b, "Explicit currency comparison", left=a, right=b)
        if comparison == ComparisonType.AMOUNT_WITHIN_TOLERANCE:
            if currency(left) != currency(right):
                return ComparisonResult(
                    ComparisonStatus.NOT_COMPARABLE,
                    "Different currencies; no foreign-exchange conversion is assumed",
                )
            a, b = decimal_value(left["amount"]), decimal_value(right["amount"])
            percent = decimal_value(parameters.get("tolerance_percent", "0"))
            if percent > 100:
                raise ValueError("Unsupported tolerance")
            allowance = a * percent / Decimal("100")
            mode = parameters.get("mode", "equal")
            if mode not in {"equal", "at_most"}:
                raise ValueError("Unknown amount comparison mode")
            equal = abs(b - a) <= allowance if mode == "equal" else b <= a + allowance
            return _result(
                equal,
                "Decimal amounts compared with explicit tolerance",
                expected=format(a, "f"),
                observed=format(b, "f"),
                currency=currency(left),
                tolerance_percent=str(percent),
                mode=mode,
            )
        if comparison == ComparisonType.QUANTITY_EQUAL:
            units = {"PCS": "PIECE", "PIECES": "PIECE", "PIECE": "PIECE", "SETS": "SET"}
            if not isinstance(left, dict) or not isinstance(right, dict):
                raise ValueError("Normalized quantities are required")
            a_unit, b_unit = left["unit"], right["unit"]
            if (
                not isinstance(a_unit, str)
                or not isinstance(b_unit, str)
                or not a_unit
                or not b_unit
            ):
                raise ValueError("Explicit units are required")
            a_unit, b_unit = (
                units.get(a_unit.upper(), a_unit.upper()),
                units.get(b_unit.upper(), b_unit.upper()),
            )
            if a_unit != b_unit:
                return ComparisonResult(
                    ComparisonStatus.NOT_COMPARABLE,
                    "Units differ; no conversion is assumed",
                    {"expected_unit": a_unit, "observed_unit": b_unit},
                )
            a, b = decimal_value(left["quantity"]), decimal_value(right["quantity"])
            return _result(a == b, "Decimal quantity and controlled unit comparison", unit=a_unit)
        if comparison == ComparisonType.DATE_ON_OR_BEFORE:
            if not all(
                isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in (left, right)
            ):
                raise ValueError("ISO dates are required")
            deadline, event = date.fromisoformat(left), date.fromisoformat(right)
            return _result(
                event <= deadline,
                "Observed date against governing deadline",
                days_after=(event - deadline).days,
            )
        if comparison == ComparisonType.CONTAINS_REQUIRED_TEXT:
            return _required_text(left, right, parameters)
        if comparison == ComparisonType.DOCUMENT_PRESENT:
            if type(left) is not bool or type(right) is not bool:
                raise ValueError("Document presence must be explicit")
            return _result(left and right, "Configured demonstration document presence check")
    except (ValueError, TypeError, KeyError, InvalidOperation):
        return ComparisonResult(
            ComparisonStatus.NOT_COMPARABLE, "Malformed or unsupported comparison input"
        )
    return ComparisonResult(ComparisonStatus.NOT_COMPARABLE, "Unsupported comparison")
