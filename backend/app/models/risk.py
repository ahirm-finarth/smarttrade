"""Append-only provider audit and detected risk findings, separate from references."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain import PK, TABLE_OPTIONS, Base, UTCDateTime, now


class RiskRun(Base):
    __tablename__ = "smart_trade_risk_runs"
    __table_args__ = (
        UniqueConstraint("case_pk", "run_number"),
        UniqueConstraint("case_pk", "request_id"),
        TABLE_OPTIONS,
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    run_number: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(String(36))
    ruleset_version: Mapped[str] = mapped_column(String(32))
    provider_set: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error_message: Mapped[str | None] = mapped_column(Text)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    input_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    checks: Mapped[list["ProviderCheck"]] = relationship(order_by="ProviderCheck.id")
    executions: Mapped[list["RiskRuleExecution"]] = relationship(order_by="RiskRuleExecution.id")
    findings: Mapped[list["RiskFinding"]] = relationship(order_by="RiskFinding.id")


class ProviderCheck(Base):
    __tablename__ = "smart_trade_provider_checks"
    __table_args__ = (UniqueConstraint("risk_run_pk", "check_key"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    risk_run_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_risk_runs.id"), index=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    check_key: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(32), index=True)
    provider_name: Mapped[str] = mapped_column(String(64))
    provider_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class RiskRuleExecution(Base):
    __tablename__ = "smart_trade_risk_rule_executions"
    __table_args__ = (
        UniqueConstraint("risk_run_pk", "provider_check_pk", "rule_id"),
        TABLE_OPTIONS,
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    risk_run_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_risk_runs.id"), index=True)
    provider_check_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_provider_checks.id"), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    rule_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class RiskFinding(Base):
    __tablename__ = "smart_trade_detected_risk_findings"
    __table_args__ = (UniqueConstraint("rule_execution_pk", "subject_value"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    risk_run_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_risk_runs.id"), index=True)
    provider_check_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_provider_checks.id"), index=True
    )
    rule_execution_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_risk_rule_executions.id"), index=True
    )
    finding_type: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))
    rule_id: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    subject_type: Mapped[str] = mapped_column(String(32))
    subject_value: Mapped[str] = mapped_column(String(255))
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
