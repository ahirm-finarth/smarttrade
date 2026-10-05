"""Immutable recommendations/audit; workflow state is a separate mutable projection."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain import PK, TABLE_OPTIONS, Base, UTCDateTime, now


class DecisionRun(Base):
    __tablename__ = "smart_trade_decision_runs"
    __table_args__ = (
        UniqueConstraint("case_pk", "run_number"),
        UniqueConstraint("case_pk", "request_id"),
        TABLE_OPTIONS,
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    run_number: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(String(36))
    examination_run_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_examination_runs.id"), index=True
    )
    risk_run_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_risk_runs.id"), index=True
    )
    ruleset_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="RUNNING")
    recommended_decision: Mapped[str | None] = mapped_column(String(16))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    input_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error_message: Mapped[str | None] = mapped_column(Text)
    reasons: Mapped[list["DecisionReason"]] = relationship(order_by="DecisionReason.id")
    workflow: Mapped["GovernedWorkflow | None"] = relationship(uselist=False)
    tasks: Mapped[list["WorkflowTask"]] = relationship(order_by="WorkflowTask.id")
    events: Mapped[list["WorkflowEvent"]] = relationship(order_by="WorkflowEvent.id")
    overrides: Mapped[list["DecisionOverride"]] = relationship(order_by="DecisionOverride.id")
    resolutions: Mapped[list["FindingResolution"]] = relationship(order_by="FindingResolution.id")


class DecisionReason(Base):
    __tablename__ = "smart_trade_decision_reasons"
    __table_args__ = (UniqueConstraint("decision_run_pk", "reason_key"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    decision_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_decision_runs.id"), index=True
    )
    reason_key: Mapped[str] = mapped_column(String(120))
    reason_type: Mapped[str] = mapped_column(String(40))
    reason_code: Mapped[str] = mapped_column(String(64), index=True)
    impact: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    source_status: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    route_to: Mapped[str | None] = mapped_column(String(32))
    documentary_finding_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_detected_discrepancies.id"), index=True
    )
    risk_finding_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_detected_risk_findings.id"), index=True
    )
    examination_execution_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_rule_executions.id"), index=True
    )
    provider_check_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_provider_checks.id"), index=True
    )
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class GovernedWorkflow(Base):
    __tablename__ = "smart_trade_governed_workflows"
    __table_args__ = (UniqueConstraint("decision_run_pk"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    decision_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_decision_runs.id"), index=True
    )
    state: Mapped[str] = mapped_column(String(32))
    final_outcome: Mapped[str | None] = mapped_column(String(16))
    maker_actor_id: Mapped[str | None] = mapped_column(String(64))
    checker_actor_id: Mapped[str | None] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    finalized_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now, onupdate=now)


class WorkflowTask(Base):
    __tablename__ = "smart_trade_workflow_tasks"
    __table_args__ = (UniqueConstraint("decision_run_pk", "task_key"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    decision_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_decision_runs.id"), index=True
    )
    task_key: Mapped[str] = mapped_column(String(100))
    task_type: Mapped[str] = mapped_column(String(32), index=True)
    assigned_role: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="OPEN")
    priority: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    reason_ids_json: Mapped[list[int]] = mapped_column(JSON)
    assigned_actor_id: Mapped[str | None] = mapped_column(String(64))
    resolution: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    assigned_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class WorkflowEvent(Base):
    __tablename__ = "smart_trade_workflow_events"
    __table_args__ = (UniqueConstraint("decision_run_pk", "request_id"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    decision_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_decision_runs.id"), index=True
    )
    task_pk: Mapped[int | None] = mapped_column(
        ForeignKey("smart_trade_workflow_tasks.id"), index=True
    )
    request_id: Mapped[str | None] = mapped_column(String(36))
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    actor_role: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class DecisionOverride(Base):
    __tablename__ = "smart_trade_decision_overrides"
    __table_args__ = (UniqueConstraint("workflow_event_pk"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    case_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_cases.id"), index=True)
    decision_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_decision_runs.id"), index=True
    )
    workflow_event_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_workflow_events.id"), index=True
    )
    actor_id: Mapped[str] = mapped_column(String(64))
    actor_role: Mapped[str] = mapped_column(String(32))
    from_decision: Mapped[str] = mapped_column(String(16))
    to_decision: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str] = mapped_column(String(64))
    rationale: Mapped[str] = mapped_column(Text)
    reason_ids_json: Mapped[list[int]] = mapped_column(JSON)
    evidence_reference: Mapped[str | None] = mapped_column(String(255))
    previous_outcome: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)


class FindingResolution(Base):
    __tablename__ = "smart_trade_finding_resolutions"
    __table_args__ = (UniqueConstraint("workflow_event_pk", "decision_reason_pk"), TABLE_OPTIONS)
    id: Mapped[int] = mapped_column(PK, primary_key=True)
    decision_run_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_decision_runs.id"), index=True
    )
    decision_reason_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_decision_reasons.id"), index=True
    )
    task_pk: Mapped[int] = mapped_column(ForeignKey("smart_trade_workflow_tasks.id"), index=True)
    workflow_event_pk: Mapped[int] = mapped_column(
        ForeignKey("smart_trade_workflow_events.id"), index=True
    )
    actor_id: Mapped[str] = mapped_column(String(64))
    actor_role: Mapped[str] = mapped_column(String(32))
    resolution: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
