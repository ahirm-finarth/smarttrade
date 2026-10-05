"""Deterministic, append-only examination of current PDF-derived evidence."""

import hashlib
import json
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models.domain import TradeCase, now
from app.models.examination import DetectedDiscrepancy, ExaminationRun, FactRelation, RuleExecution
from app.rules import RULESET_VERSION, load_rules
from app.services.comparisons import ComparisonResult, ComparisonStatus, compare
from app.services.documents import DocumentConflict
from app.services.fact_resolver import case_by_id, load_case_evidence, resolve


class ExaminationNotFound(Exception):
    pass


class ExaminationNotConfigured(ValueError):
    pass


def fingerprint(snapshot: dict) -> str:
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def compare_resolutions(rule, left, right) -> ComparisonResult:
    reasons = f"Expected: {left.reason}. Observed: {right.reason}."
    for state in ("NEEDS_REVIEW", "NOT_COMPARABLE"):
        if state in {left.state, right.state}:
            return ComparisonResult(ComparisonStatus(state), reasons)
    parameters = dict(rule.parameters)
    if right.evidence:
        parameters["observed_field"] = right.evidence["field_name"]
    return compare(
        rule.comparison,
        left.evidence["comparison_value"] if left.state == "READY" else None,
        right.evidence["comparison_value"] if right.state == "READY" else None,
        parameters,
    )


def run_examination(
    session: Session, settings: Settings, case_id: str, request_id: str | None = None
):
    case = case_by_id(session, case_id)
    case = session.scalar(select(TradeCase).where(TradeCase.id == case.id).with_for_update())
    key = request_id or str(uuid4())
    repeated = session.scalar(
        select(ExaminationRun).where(
            ExaminationRun.case_pk == case.id, ExaminationRun.request_id == key
        )
    )
    if repeated:
        session.commit()
        return get_examination(session, repeated.id)
    latest = session.scalar(
        select(ExaminationRun)
        .where(ExaminationRun.case_pk == case.id)
        .order_by(ExaminationRun.run_number.desc())
        .limit(1)
    )
    if latest and latest.status == "RUNNING":
        if latest.started_at > now() - timedelta(minutes=5):
            session.rollback()
            raise DocumentConflict("A documentary examination is already running")
        latest.status, latest.completed_at = "FAILED", now()
        latest.error_message = "Previous examination worker expired; history preserved"
    try:
        rules = load_rules(case.product_playbook)
    except ValueError:
        session.rollback()
        raise ExaminationNotConfigured(
            "No documentary examination playbook is configured"
        ) from None
    corpus = load_case_evidence(session, case)
    snapshot = {
        "evidence": corpus,
        "rules": [r.model_dump(mode="json") for r in rules],
        "confidence_threshold": str(settings.examination_min_confidence),
    }
    run = ExaminationRun(
        case_pk=case.id,
        run_number=latest.run_number + 1 if latest else 1,
        request_id=key,
        playbook=case.product_playbook,
        ruleset_version=RULESET_VERSION,
        input_snapshot_json=snapshot,
        input_fingerprint=fingerprint(snapshot),
        status="RUNNING",
    )
    session.add(run)
    session.commit()
    run_id = run.id
    try:
        statuses = Counter()
        relation_count = finding_count = 0
        for rule in rules:
            left = resolve(corpus, rule.left, settings.examination_min_confidence)
            right = resolve(corpus, rule.right, settings.examination_min_confidence)
            result = compare_resolutions(rule, left, right)
            statuses[result.status.value] += 1
            left_id = left.evidence.get("fact_id") if left.evidence else None
            right_id = right.evidence.get("fact_id") if right.evidence else None
            execution = RuleExecution(
                examination_run_pk=run.id,
                rule_id=rule.id,
                rule_version=rule.version,
                comparison_type=rule.comparison.value,
                status=result.status.value,
                left_fact_pk=left_id,
                right_fact_pk=right_id,
                rule_snapshot_json=rule.model_dump(mode="json"),
                input_json={"expected": left.snapshot(), "observed": right.snapshot()},
                output_json={
                    "status": result.status.value,
                    "reason": result.reason,
                    "details": result.details,
                },
            )
            session.add(execution)
            session.flush()
            if left_id is not None and right_id is not None:
                session.add(
                    FactRelation(
                        case_pk=case.id,
                        examination_run_pk=run.id,
                        rule_execution_pk=execution.id,
                        source_fact_pk=left_id,
                        target_fact_pk=right_id,
                        relation_type=rule.relation_type,
                        comparison_type=rule.comparison.value,
                        status=result.status.value,
                        confidence=min(
                            Decimal(left.evidence["confidence"]),
                            Decimal(right.evidence["confidence"]),
                        ),
                    )
                )
                relation_count += 1
            # Extraction absence/uncertainty never creates a business mismatch.
            if result.status == ComparisonStatus.MISMATCH and left.state == right.state == "READY":
                session.add(
                    DetectedDiscrepancy(
                        case_pk=case.id,
                        examination_run_pk=run.id,
                        rule_execution_pk=execution.id,
                        finding_type=rule.finding_type,
                        title=rule.finding_type.replace("_", " ").capitalize(),
                        description=rule.name + ": " + result.reason,
                        severity=rule.severity,
                        rule_id=rule.id,
                        rule_version=rule.version,
                        expected_fact_pk=left_id,
                        observed_fact_pk=right_id,
                        expected_json=left.evidence,
                        observed_json=right.evidence,
                        status="OPEN",
                    )
                )
                finding_count += 1
        incomplete = sum(
            count for status, count in statuses.items() if status not in {"MATCH", "MISMATCH"}
        )
        run.summary_json = {
            "rules_executed": len(rules),
            "matched": statuses["MATCH"],
            "mismatched": statuses["MISMATCH"],
            "findings": finding_count,
            "incomplete": incomplete,
            "relations": relation_count,
            "results_by_status": dict(statuses),
            "confidence_threshold": str(settings.examination_min_confidence),
            "fact_count": sum(len(d["facts"]) for d in corpus["documents"]),
        }
        run.status = (
            "DISCREPANCIES_FOUND"
            if finding_count
            else "INCOMPLETE_EXAMINATION"
            if incomplete
            else "CLEAN"
        )
        run.completed_at = now()
        session.commit()
    except Exception:
        session.rollback()
        run = session.get(ExaminationRun, run_id)
        run.status, run.completed_at = "FAILED", now()
        run.error_message = "Documentary examination failed; internal details are suppressed"
        session.commit()
    return get_examination(session, run_id)


def get_examination(session: Session, run_id: int) -> ExaminationRun:
    run = session.scalar(
        select(ExaminationRun)
        .where(ExaminationRun.id == run_id)
        .options(
            selectinload(ExaminationRun.executions),
            selectinload(ExaminationRun.findings),
            selectinload(ExaminationRun.relations),
        )
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise ExaminationNotFound
    return run


def examination_history(session: Session, case_id: str) -> list[ExaminationRun]:
    case = case_by_id(session, case_id)
    return list(
        session.scalars(
            select(ExaminationRun)
            .where(ExaminationRun.case_pk == case.id)
            .order_by(ExaminationRun.run_number.desc())
        )
    )


def examination_is_current(
    session: Session, run: ExaminationRun, settings: Settings | None = None
) -> bool:
    case = session.get(TradeCase, run.case_pk)
    try:
        rules = load_rules(case.product_playbook)
    except ValueError:
        return False
    snapshot = {
        "evidence": load_case_evidence(session, case),
        "rules": [r.model_dump(mode="json") for r in rules],
        "confidence_threshold": str((settings or get_settings()).examination_min_confidence),
    }
    return fingerprint(snapshot) == run.input_fingerprint
