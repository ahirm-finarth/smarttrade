"""Read-only chronological view of existing source runs and governed events."""

from sqlalchemy import select

from app.models.decision import DecisionOverride, DecisionRun, WorkflowEvent
from app.models.documents import DocumentProcessingRun, DocumentVersion
from app.models.examination import ExaminationRun
from app.models.risk import RiskRun
from app.schemas.decision import AuditEntry
from app.services.fact_resolver import case_by_id


def case_audit(session, case_id):
    case = case_by_id(session, case_id)
    entries = []

    def add(kind, id, time, summary, url, actor="system", role="SYSTEM", detail=None):
        entries.append(
            AuditEntry(
                id=f"{kind}:{id}",
                timestamp=time,
                event_type=kind,
                actor_id=actor,
                actor_role=role,
                summary=summary,
                source_url=url,
                source_id=id,
                detail=detail or {},
            )
        )

    for run, version in session.execute(
        select(DocumentProcessingRun, DocumentVersion)
        .join(DocumentVersion, DocumentProcessingRun.document_version_pk == DocumentVersion.id)
        .where(DocumentVersion.case_pk == case.id)
    ):
        add(
            "DOCUMENT_PROCESSING",
            run.id,
            run.completed_at or run.started_at,
            f"{version.original_filename}: {run.status}",
            f"/documents/{version.document_pk}?version_id={version.id}&run_id={run.id}",
        )
    for model, kind, tab, parameter in (
        (ExaminationRun, "DOCUMENTARY_EXAMINATION", "examination", "examination_run_id"),
        (RiskRun, "RISK_RUN", "risk_compliance", "risk_run_id"),
        (DecisionRun, "DECISION_RUN", "decision", "decision_id"),
    ):
        for run in session.scalars(select(model).where(model.case_pk == case.id)):
            recommendation = getattr(run, "recommended_decision", None)
            add(
                kind,
                run.id,
                run.completed_at or run.started_at,
                f"Run {run.run_number}: {run.status}"
                + (f" · {recommendation}" if recommendation else ""),
                f"/cases/{case_id}?tab={tab}&{parameter}={run.id}",
                detail=run.summary_json,
            )
    overrides = {
        o.workflow_event_pk: o.id
        for o in session.scalars(
            select(DecisionOverride).where(DecisionOverride.case_pk == case.id)
        )
    }
    for event in session.scalars(select(WorkflowEvent).where(WorkflowEvent.case_pk == case.id)):
        detail = {**event.metadata_json}
        if event.id in overrides:
            detail["override_id"] = overrides[event.id]
        add(
            event.event_type,
            event.id,
            event.created_at,
            event.comment or event.event_type.replace("_", " ").capitalize(),
            f"/cases/{case_id}?tab=workflow&decision_id={event.decision_run_pk}"
            + (f"#workflow-task-{event.task_pk}" if event.task_pk else ""),
            event.actor_id,
            event.actor_role,
            detail,
        )
    return sorted(entries, key=lambda e: (e.timestamp, e.event_type, e.source_id), reverse=True)
