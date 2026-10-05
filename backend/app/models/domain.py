from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

TABLE_OPTIONS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
PK = BigInteger().with_variant(Integer, "sqlite")


class UTCDateTime(TypeDecorator):
    """MySQL stores naive UTC; the application always receives aware UTC values."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Timestamps must include a timezone")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value else None


def now():
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TradeCase(Base):
    __tablename__ = "smart_trade_cases"
    __table_args__ = TABLE_OPTIONS

    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64), unique=True)
    dataset_key: Mapped[str | None] = mapped_column(String(64), index=True)
    scenario: Mapped[str | None] = mapped_column(String(160))
    product_playbook: Mapped[str | None] = mapped_column(String(100), index=True)
    direction: Mapped[str | None] = mapped_column(String(32))
    applicant: Mapped[str | None] = mapped_column(String(200))
    beneficiary: Mapped[str | None] = mapped_column(String(200))
    customer_id: Mapped[str | None] = mapped_column(String(64))
    facility_id: Mapped[str | None] = mapped_column(String(64))
    currency: Mapped[str | None] = mapped_column(String(3))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    priority: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(160))
    expected_decision: Mapped[str | None] = mapped_column(String(16), index=True)
    demo_narrative: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now, onupdate=now)
    parties: Mapped[list["CaseParty"]] = relationship(cascade="all, delete-orphan")
    documents: Mapped[list["CaseDocument"]] = relationship(cascade="all, delete-orphan")
    trade_lines: Mapped[list["TradeLine"]] = relationship(cascade="all, delete-orphan")
    discrepancies: Mapped[list["Discrepancy"]] = relationship(cascade="all, delete-orphan")
    risk_events: Mapped[list["RiskEvent"]] = relationship(cascade="all, delete-orphan")
    approvals: Mapped[list["ApprovalEvent"]] = relationship(cascade="all, delete-orphan")


class CaseRelated:
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    source_key: Mapped[str] = mapped_column(String(64))

    @declared_attr.directive
    def __table_args__(cls):
        return (UniqueConstraint("case_pk", "source_key"), TABLE_OPTIONS)


class CaseParty(CaseRelated, Base):
    __tablename__ = "smart_trade_case_parties"
    party_role: Mapped[str | None] = mapped_column(String(64))
    party_name: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(2))
    screening_status: Mapped[str | None] = mapped_column(String(32))


class CaseDocument(CaseRelated, Base):
    __tablename__ = "smart_trade_case_documents"
    document_id: Mapped[str | None] = mapped_column(String(64))
    document_type: Mapped[str | None] = mapped_column(String(100))
    reference: Mapped[str | None] = mapped_column(String(100))
    expected: Mapped[bool | None]
    received: Mapped[bool | None]
    file_name: Mapped[str | None] = mapped_column(String(255))
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class TradeLine(CaseRelated, Base):
    __tablename__ = "smart_trade_trade_lines"
    source: Mapped[str | None] = mapped_column(String(64))
    item_no: Mapped[int | None]
    goods_description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    uom: Mapped[str | None] = mapped_column(String(32))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    line_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))


class Discrepancy(CaseRelated, Base):
    __tablename__ = "smart_trade_discrepancies"
    finding_id: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str | None] = mapped_column(String(32))
    rule_id: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(100))
    field: Mapped[str | None] = mapped_column(String(100))
    expected_value: Mapped[str | None] = mapped_column(Text)
    observed_value: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    route_to: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(32))


class RiskEvent(CaseRelated, Base):
    __tablename__ = "smart_trade_risk_events"
    risk_id: Mapped[str | None] = mapped_column(String(64))
    risk_type: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String(200))
    provider: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[str | None] = mapped_column(String(32))
    severity: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)


class ApprovalEvent(CaseRelated, Base):
    __tablename__ = "smart_trade_approval_events"
    event_time: Mapped[datetime | None] = mapped_column(UTCDateTime())
    actor_role: Mapped[str | None] = mapped_column(String(100))
    actor_id: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(32))


class DemoRiskRule(Base):
    """Passive source reference only; Phase 1 never executes this logic."""

    __tablename__ = "smart_trade_demo_risk_rules"
    __table_args__ = TABLE_OPTIONS
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(64), unique=True)
    dataset_key: Mapped[str] = mapped_column(String(64), index=True)
    playbook: Mapped[str | None] = mapped_column(String(100))
    control_type: Mapped[str | None] = mapped_column(String(64))
    logic: Mapped[str | None] = mapped_column(Text)
    default_route: Mapped[str | None] = mapped_column(String(100))


class DemoScreeningReference(Base):
    """Synthetic reference inventory; no screening integration is invoked."""

    __tablename__ = "smart_trade_demo_screening_references"
    __table_args__ = TABLE_OPTIONS
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(64), unique=True)
    dataset_key: Mapped[str] = mapped_column(String(64), index=True)
    reference_type: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(2))
    status: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)
