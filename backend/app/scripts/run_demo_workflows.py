"""Explicit synthetic workflow demo; appends actions and preserves source evidence."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.domain import TradeCase
from app.rules.decision import POLICY
from app.rules.workflow import Action, TaskType
from app.schemas.workflow import OverrideRequest, TaskActionRequest
from app.services.decision_engine import generate_decision
from app.services.decision_overrides import apply_override
from app.services.governed_workflow import act_on_task, open_tasks, unresolved_reason_ids

ACTOR = {
    TaskType.TRADE: "trade.demo",
    TaskType.COMPLIANCE: "compliance.demo",
    TaskType.LEGAL: "legal.demo",
}


def act(session, settings, run, task, actor, action, rationale):
    return act_on_task(
        session,
        settings,
        task.id,
        TaskActionRequest(
            actor_id=actor,
            action=action,
            comment=rationale,
            expected_revision=run.workflow.revision,
        ),
    )


def demonstrate(session, settings, case_id):
    run = generate_decision(session, settings, case_id)
    assert run.status == "COMPLETED"
    initial = run.recommended_decision
    if initial == "REFER":
        for task in list(open_tasks(run, set(ACTOR))):
            reasons = [r for r in run.reasons if r.id in task.reason_ids_json]
            missing = any(r.reason_code not in POLICY.overrideable_codes for r in reasons)
            action = (
                Action.INFORMATION
                if missing
                else (
                    Action.CLEAR
                    if all(r.reason_code == "RISK_REVIEW" for r in reasons)
                    else Action.ISSUE
                )
            )
            run = act(
                session,
                settings,
                run,
                task,
                ACTOR[task.task_type],
                action,
                (
                    "Synthetic demonstration only: request source-supported comparison "
                    "review; no breach or clearance inferred."
                )
                if missing
                else (
                    "Synthetic specialist demonstration: review-level demo signal "
                    "cleared; no live provider clearance asserted."
                )
                if action == Action.CLEAR
                else (
                    "Synthetic specialist demonstration: documentary mismatch confirmed "
                    "against the saved original source evidence."
                ),
            )
        remaining = unresolved_reason_ids(run)
        latest = {r.decision_reason_pk: r.resolution for r in run.resolutions}
        if remaining and all(
            r.reason_code in POLICY.overrideable_codes and latest.get(r.id) == Action.ISSUE
            for r in run.reasons
            if r.id in remaining
        ):
            run = apply_override(
                session,
                settings,
                run.id,
                OverrideRequest(
                    actor_id="supervisor.demo",
                    reason_code="ACCEPT_REVIEWED_EXCEPTION",
                    rationale=(
                        "Synthetic training acceptance of specialist-confirmed documentary "
                        "exceptions, without real customer waiver or execution authority."
                    ),
                    reason_ids=sorted(remaining),
                    evidence_reference=f"Synthetic decision #{run.id} source snapshot",
                    expected_revision=run.workflow.revision,
                ),
            )
    if run.workflow.state == "AWAITING_MAKER":
        run = act(
            session,
            settings,
            run,
            open_tasks(run, {TaskType.MAKER})[0],
            "maker.demo",
            Action.SUBMIT,
            (
                "Synthetic maker review of the saved decision, specialist resolutions "
                "and any recorded exception acceptance."
            ),
        )
        run = act(
            session,
            settings,
            run,
            open_tasks(run, {TaskType.CHECKER})[0],
            "checker.demo",
            Action.APPROVE,
            (
                "Synthetic independent checker review; all configured demo "
                "prerequisites complete. No payment or posting authorized."
            ),
        )
    assert run.recommended_decision == initial
    return {
        "case_id": case_id,
        "decision_id": run.id,
        "system_recommendation": initial,
        "workflow_state": run.workflow.state,
        "final_outcome": run.workflow.final_outcome,
        "examination_id": run.examination_run_pk,
        "risk_id": run.risk_run_pk,
        "tasks": [{"id": t.id, "kind": t.task_type, "status": t.status} for t in run.tasks],
        "resolution_ids": [r.id for r in run.resolutions],
        "override_ids": [o.id for o in run.overrides],
        "events": [{"id": e.id, "type": e.event_type, "actor": e.actor_id} for e in run.events],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with Session(get_engine()) as session:
            ids = session.scalars(select(TradeCase.case_id).order_by(TradeCase.case_id)).all()
            report = {
                "synthetic_only": True,
                "results": [demonstrate(session, get_settings(), id) for id in ids],
            }
    except Exception:
        print("Workflow demonstration failed; private diagnostics suppressed.")
        raise SystemExit(1) from None
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n")
    print(serialized)


if __name__ == "__main__":
    main()
