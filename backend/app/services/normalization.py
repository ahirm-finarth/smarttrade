"""Deterministic value normalization after extraction; Decimal, never float money."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

CURRENCIES = {"USD", "EUR", "INR", "GBP", "JPY", "CNY", "CHF", "AED", "SGD", "CAD", "AUD"}
NUMBER = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3}|\d+)(?:\.\d+)?"


class NormalizationError(ValueError):
    pass


def decimal_text(raw: str) -> str:
    if not re.fullmatch(NUMBER, raw):
        raise NormalizationError("Numeric value is ambiguous or malformed")
    try:
        value = Decimal(raw.replace(",", ""))
        if not value.is_finite() or len(value.as_tuple().digits) > 20:
            raise NormalizationError("Numeric value exceeds supported precision")
        return format(value, "f")
    except InvalidOperation:
        raise NormalizationError("Numeric value is invalid") from None


def normalize_money(raw: str) -> dict[str, str]:
    text = " ".join(raw.split()).upper()
    codes = re.findall(r"\b[A-Z]{3}\b", text)
    if len(codes) != 1 or codes[0] not in CURRENCIES:
        raise NormalizationError("An explicit supported currency code is required")
    currency = codes[0]
    text = text.replace(currency, "").strip()
    # Currency symbols are only accepted with an explicit matching currency code.
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥", "CNY": "¥"}
    symbol = symbols.get(currency)
    if symbol:
        text = text.replace(symbol, "").strip()
    amount = Decimal(decimal_text(text))
    if amount.as_tuple().exponent < -2:
        raise NormalizationError("Money has unsupported fractional precision")
    return {"amount": format(amount.quantize(Decimal("0.01")), "f"), "currency": currency}


def normalize_date(raw: str) -> str:
    text = " ".join(raw.split())
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise NormalizationError("Date is invalid or ambiguous")


def normalize_quantity(raw: str) -> dict[str, str]:
    match = re.fullmatch(rf"\s*({NUMBER})\s+([A-Za-z][A-Za-z0-9 ./-]{{0,31}})\s*", raw)
    if not match:
        raise NormalizationError("Quantity requires an explicit number and unit")
    return {"quantity": decimal_text(match[1]), "unit": match[2].strip().upper()}


def normalize_boolean(raw: str) -> bool:
    text = " ".join(raw.casefold().split())
    if text in {"false", "no", "not allowed", "prohibited"} or text.endswith(" not allowed"):
        return False
    if text in {"true", "yes", "allowed", "permitted"} or text.endswith(" allowed"):
        return True
    raise NormalizationError("Boolean value is not explicit")


def normalize_value(kind: str, raw: str) -> Any:
    normalizers = {
        "money": normalize_money,
        "date": normalize_date,
        "quantity": normalize_quantity,
        "boolean": normalize_boolean,
    }
    if kind == "text":
        return " ".join(raw.split())
    if kind not in normalizers:
        raise NormalizationError("Unsupported normalization kind")
    return normalizers[kind](raw)
