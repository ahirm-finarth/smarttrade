"""Append-only documentary examination, separate from synthetic reference findings."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain import PK, TABLE_OPTIONS, Base, UTCDateTime, now


class ExaminationRun(Base):
    __tablename__ = "smart_trade_examination_runs"
    __table_args__ = (
        UniqueConstraint("case_pk", "run_number"),
        UniqueConstraint("case_pk", "request_id"),
        TABLE_OPTIONS,
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    run_number: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(String(36))
    playbook: Mapped[str] = mapped_column(String(100))
    ruleset_version: Mapped[str] = mapped_column(String(32))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error_message: Mapped[str | None] = mapped_column(Text)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    input_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    executions: Mapped[list["RuleExecution"]] = relationship(order_by="RuleExecution.id")
    relations: Mapped[list["FactRelation"]] = relationship(order_by="FactRelation.id")
    findings: Mapped[list["DetectedDiscrepancy"]] = relationship(order_by="DetectedDiscrepancy.id")


class RuleExecution(Base):
    __tablename__ = "smart_trade_rule_executions"
    __table_args__ = (UniqueConstraint("examination_run_pk", "rule_id"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    examination_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_examination_runs.id"), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[int] = mapped_column(Integer)
    comparison_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    left_fact_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_extracted_facts.id"), index=True
    )
    right_fact_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_extracted_facts.id"), index=True
    )
    rule_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class FactRelation(Base):
    __tablename__ = "smart_trade_fact_relations"
    __table_args__ = (UniqueConstraint("rule_execution_pk"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    examination_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_examination_runs.id"), index=True
    )
    rule_execution_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_rule_executions.id"), index=True
    )
    source_fact_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_extracted_facts.id"), index=True
    )
    target_fact_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_extracted_facts.id"), index=True
    )
    relation_type: Mapped[str] = mapped_column(String(32))
    comparison_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class DetectedDiscrepancy(Base):
    __tablename__ = "smart_trade_detected_discrepancies"
    __table_args__ = (UniqueConstraint("rule_execution_pk"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    examination_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_examination_runs.id"), index=True
    )
    rule_execution_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_rule_executions.id"), index=True
    )
    finding_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))
    rule_id: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    expected_fact_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_extracted_facts.id"), index=True
    )
    observed_fact_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_extracted_facts.id"), index=True
    )
    expected_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    observed_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
