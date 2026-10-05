"""Explicit synthetic goods policies and Decimal price bands; empty by default."""

from decimal import Decimal

from pydantic import Field, model_validator

from app.integrations.risk.contracts import (
    Category,
    ProviderInput,
    ProviderResult,
    SafeModel,
)
from app.services.comparisons import decimal_value, normalized_text


class GoodsPolicy(SafeModel):
    reference_id: str
    goods: str
    reason: str
    status: str = Field(pattern="^(CLEAR|NEEDS_REVIEW|HIT)$")


class PriceBand(SafeModel):
    reference_id: str
    goods: str
    currency: str = Field(pattern="^[A-Z]{3}$")
    unit: str
    minimum: str
    maximum: str

    @model_validator(mode="after")
    def bounds(self):
        if decimal_value(self.minimum) > decimal_value(self.maximum):
            raise ValueError("Invalid price range")
        return self


class SyntheticGoodsRiskProvider:
    category = Category.GOODS
    name = "SYNTHETIC_GOODS"
    version = "goods-v1"

    def __init__(self, policies: list[GoodsPolicy] | None = None):
        self.policies = policies or []

    def snapshot(self):
        return {
            "category": self.category,
            "name": self.name,
            "version": self.version,
            "policies": [p.model_dump(mode="json") for p in self.policies],
        }

    def check(self, subject: ProviderInput):
        if not subject.subject:
            return ProviderResult(status="NOT_APPLICABLE", reason="No goods description")
        matches = [
            p for p in self.policies if normalized_text(p.goods) == normalized_text(subject.subject)
        ]
        if len(matches) > 1:
            return ProviderResult(
                status="INSUFFICIENT_DATA", reason="Conflicting synthetic goods policies"
            )
        if not matches:
            return ProviderResult(
                status="NOT_CHECKED",
                reason="No supplied synthetic goods policy; no legal classification claimed",
            )
        p = matches[0]
        return ProviderResult(
            status=p.status, reason=p.reason, details={"policy": p.model_dump(mode="json")}
        )


class SyntheticFairValueProvider:
    category = Category.FAIR_VALUE
    name = "SYNTHETIC_FAIR_VALUE"
    version = "fair-value-v1"

    def __init__(self, bands: list[PriceBand] | None = None):
        self.bands = bands or []

    def snapshot(self):
        return {
            "category": self.category,
            "name": self.name,
            "version": self.version,
            "price_bands": [b.model_dump(mode="json") for b in self.bands],
        }

    def check(self, subject: ProviderInput):
        if not subject.subject:
            return ProviderResult(status="NOT_APPLICABLE", reason="No commercial goods/price input")
        trade = subject.trade
        price, quantity, money = (
            trade.get("unit_price"),
            trade.get("quantity"),
            trade.get("total_amount"),
        )
        if not isinstance(quantity, dict) or not (
            isinstance(price, dict) or isinstance(money, dict)
        ):
            return ProviderResult(
                status="INSUFFICIENT_DATA",
                reason="Unit, quantity and explicit currency/amount are required",
            )
        try:
            q = decimal_value(quantity["quantity"])
            if q <= 0:
                raise ValueError("Zero quantity")
            observed = (
                decimal_value(price["amount"]) if price else decimal_value(money["amount"]) / q
            )
            currency = (price or money)["currency"]
            unit = quantity["unit"]
        except (ValueError, KeyError):
            return ProviderResult(
                status="INSUFFICIENT_DATA", reason="Price inputs cannot be normalized safely"
            )
        details = {
            "observed_unit_price": format(observed, "f"),
            "currency": currency,
            "unit": unit,
            "derivation": "Extracted unit price" if price else "Invoice total / extracted quantity",
        }
        bands = [
            b
            for b in self.bands
            if normalized_text(b.goods) == normalized_text(subject.subject)
            and b.currency == currency
            and normalized_text(b.unit) == normalized_text(unit)
        ]
        if not bands:
            return ProviderResult(
                status="NOT_CHECKED",
                reason="No matching synthetic price band; no reference market price invented",
                details=details,
            )
        if len(bands) > 1:
            return ProviderResult(
                status="INSUFFICIENT_DATA",
                reason="Ambiguous synthetic price bands",
                details=details,
            )
        band = bands[0]
        low, high = Decimal(band.minimum), Decimal(band.maximum)
        return ProviderResult(
            status="CLEAR" if low <= observed <= high else "NEEDS_REVIEW",
            reason="Observed unit price compared with explicit synthetic reference range",
            details={
                **details,
                "reference": band.model_dump(mode="json"),
                "variance_above_max": format(observed - high, "f"),
            },
        )
