import pytest
from pydantic import ValidationError

from app.integrations.risk.contracts import ProviderInput
from app.integrations.risk.trade_policy import (
    GoodsPolicy,
    PriceBand,
    SyntheticFairValueProvider,
    SyntheticGoodsRiskProvider,
)


def subject(price="120.00", currency="USD", unit="MT"):
    return ProviderInput(
        subject_type="goods",
        subject="Unit test goods",
        trade={
            "unit_price": {"amount": price, "currency": currency},
            "quantity": {"quantity": "10", "unit": unit},
        },
    )


def band():
    return PriceBand(
        reference_id="UNIT-BAND",
        goods="Unit test goods",
        currency="USD",
        unit="MT",
        minimum="80.00",
        maximum="105.00",
    )


def test_absent_price_reference_never_becomes_clear_or_invented_price():
    result = SyntheticFairValueProvider().check(subject())
    assert result.status == "NOT_CHECKED" and "reference" not in result.details


@pytest.mark.parametrize(
    "price,status", [("105.00", "CLEAR"), ("120.00", "NEEDS_REVIEW"), ("NaN", "INSUFFICIENT_DATA")]
)
def test_explicit_synthetic_price_band_uses_decimal(price, status):
    assert SyntheticFairValueProvider([band()]).check(subject(price)).status == status


def test_different_currency_or_unit_no_fx_or_conversion():
    provider = SyntheticFairValueProvider([band()])
    assert provider.check(subject(currency="EUR")).status == "NOT_CHECKED"
    assert provider.check(subject(unit="KG")).status == "NOT_CHECKED"


def test_goods_only_follow_explicit_policy():
    assert SyntheticGoodsRiskProvider().check(subject()).status == "NOT_CHECKED"
    policy = GoodsPolicy(
        reference_id="UNIT-POLICY",
        goods="Unit test goods",
        reason="Synthetic fixture review only",
        status="NEEDS_REVIEW",
    )
    assert SyntheticGoodsRiskProvider([policy]).check(subject()).status == "NEEDS_REVIEW"


def test_invalid_price_band_and_optional_absence():
    with pytest.raises(ValidationError):
        PriceBand(
            reference_id="x", goods="test", currency="USD", unit="MT", minimum="106", maximum="105"
        )
    absent = ProviderInput(subject_type="goods")
    assert SyntheticFairValueProvider().check(absent).status == "NOT_APPLICABLE"
