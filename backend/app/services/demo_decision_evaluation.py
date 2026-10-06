"""Offline reference-label evaluation, never imported by runtime decision/workflow code."""

from sqlalchemy import select

from app.models.decision import DecisionRun
from app.models.domain import TradeCase
from app.services.decision_engine import latest_source


def score(rows):
    correct = sum(r["expected"] == r["recommended"] for r in rows)
    classes = {}
    for label in ("PASS", "REFER", "BLOCK"):
        tp = sum(r["expected"] == label and r["recommended"] == label for r in rows)
        fp = sum(r["expected"] != label and r["recommended"] == label for r in rows)
        fn = sum(r["expected"] == label and r["recommended"] != label for r in rows)
        support = sum(r["expected"] == label for r in rows)
        classes[label] = {
            "support": support,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        }
    return {
        "cases": len(rows),
        "correct": correct,
        "accuracy": correct / len(rows) if rows else None,
        "classes": classes,
        "results": rows,
        "scope": "Synthetic five-case system recommendations only; human overrides are not labels.",
        "limitations": [
            "No reference BLOCK case; test coverage uses an isolated confirmed fixture.",
            "Synthetic accuracy does not establish production accuracy or live clearance.",
            (
                "The demo policy explicitly excludes unavailable country/goods/price "
                "references and the absent financing ledger from mandatory controls."
            ),
        ],
    }


def evaluate_demo_decisions(session):
    rows = []
    # Expected labels are accessed only here, after persisted system recommendations exist.
    for case in session.scalars(select(TradeCase).order_by(TradeCase.case_id)):
        run = latest_source(session, DecisionRun, case.id)
        rows.append(
            {
                "case_id": case.case_id,
                "decision_id": run.id if run else None,
                "status": run.status if run else "MISSING",
                "expected": case.expected_decision,
                "recommended": run.recommended_decision if run else None,
                "workflow_state": run.workflow.state if run and run.workflow else None,
                "final_outcome": run.workflow.final_outcome if run and run.workflow else None,
            }
        )
    return score(rows)
