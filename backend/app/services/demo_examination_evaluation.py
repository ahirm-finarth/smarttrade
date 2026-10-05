"""Offline labelled evaluation. Never imported by runtime examination or APIs."""

import csv
from collections import Counter
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import TradeCase
from app.models.examination import ExaminationRun
from app.services.normalization import normalize_date, normalize_money, normalize_quantity

REFERENCES = Path(__file__).resolve().parents[3] / "data" / "raw" / "discrepancies.csv"
REFERENCE_FAMILIES = {
    "LC-AMOUNT-001": "AMOUNT_MISMATCH",
    "LC-QTY-001": "QUANTITY_MISMATCH",
    "LC-SHIP-DATE-001": "LATE_SHIPMENT",
    "LC-PO-REF-001": "PURCHASE_ORDER_MISMATCH",
    "BG-DEMAND-STATEMENT-001": "REQUIRED_BREACH_STATEMENT_MISSING",
}


def values_match(reference: dict, finding: dict) -> bool:
    """Check actual values where reference and normalized source types align."""
    family = finding["finding_type"]
    expected, observed = finding["expected"], finding["observed"]
    if family == "AMOUNT_MISMATCH":
        return expected == normalize_money(
            reference["expected_value"]
        ) and observed == normalize_money(reference["observed_value"])
    if family == "QUANTITY_MISMATCH":
        return expected == normalize_quantity(
            reference["expected_value"]
        ) and observed == normalize_quantity(reference["observed_value"])
    if family == "LATE_SHIPMENT":
        return expected == normalize_date(
            reference["expected_value"].removeprefix("On or before ")
        ) and observed == normalize_date(reference["observed_value"])
    if family == "PURCHASE_ORDER_MISMATCH":
        return expected == reference["expected_value"] and observed == reference["observed_value"]
    # These differently worded labels describe the same supported documentary condition.
    # The engine independently requires source-backed requirement AND explicit absence.
    return family == "REQUIRED_BREACH_STATEMENT_MISSING"


def score_findings(references: list[dict], findings: list[dict]) -> dict:
    applicable = [r for r in references if r["rule_id"] in REFERENCE_FAMILIES]
    excluded = [r for r in references if r["rule_id"] not in REFERENCE_FAMILIES]
    matches = []
    missed = []
    accounted = set()
    for reference in applicable:
        ids = [
            f["id"]
            for f in findings
            if f["case_id"] == reference["case_id"]
            and f["finding_type"] == REFERENCE_FAMILIES[reference["rule_id"]]
            and values_match(reference, f)
        ]
        if ids:
            matches.append(
                {
                    "reference_id": reference["finding_id"],
                    "case_id": reference["case_id"],
                    "family": REFERENCE_FAMILIES[reference["rule_id"]],
                    "detected_finding_ids": ids,
                }
            )
            accounted.update(ids)
        else:
            missed.append(
                {
                    "reference_id": reference["finding_id"],
                    "case_id": reference["case_id"],
                    "family": REFERENCE_FAMILIES[reference["rule_id"]],
                }
            )
    unmatched = [f for f in findings if f["id"] not in accounted]
    # Reference quantity label covers both LC/invoice and LC/packing comparisons.
    # Publish raw counts alongside the case/family unit; never discard an execution.
    fp_keys = {(f["case_id"], f["finding_type"]) for f in unmatched}
    tp, fp, fn = len(matches), len(fp_keys), len(missed)
    precision = Decimal(tp) / Decimal(tp + fp) if tp + fp else Decimal(0)
    recall = Decimal(tp) / Decimal(tp + fn) if tp + fn else Decimal(0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else Decimal(0)
    return {
        "unit": "labelled case/finding-family; matching normalized values where representable",
        "expected_discrepancies": len(applicable),
        "detected_raw_findings": len(findings),
        "detected_case_families": len({(f["case_id"], f["finding_type"]) for f in findings}),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": str(precision.quantize(Decimal("0.0001"))),
        "recall": str(recall.quantize(Decimal("0.0001"))),
        "f1": str(f1.quantize(Decimal("0.0001"))),
        "matched_references": matches,
        "missed_references": missed,
        "unmatched_findings": unmatched,
        "additional_matching_comparisons": sum(
            max(0, len(m["detected_finding_ids"]) - 1) for m in matches
        ),
        "excluded_references": [
            {
                "reference_id": r["finding_id"],
                "rule_id": r["rule_id"],
                "reason": (
                    "No Phase 3 documentary mapping; duplicate financing/risk is out of scope"
                ),
            }
            for r in excluded
        ],
        "value_mapping_note": (
            "Amount, quantity, date and PO require matching values. "
            "Breach absence is a controlled semantic family, "
            "not verbatim reference text accuracy."
        ),
    }


def evaluate_demo_examination(session: Session, reference_path: Path = REFERENCES) -> dict:
    # Read labels only here, AFTER persisted examination; no calls to the engine.
    with reference_path.open(newline="", encoding="utf-8-sig") as source:
        references = list(csv.DictReader(source))
    cases = session.scalars(select(TradeCase).order_by(TradeCase.case_id)).all()
    runs, findings, case_reports = [], [], []
    for case in cases:
        run = session.scalar(
            select(ExaminationRun)
            .where(ExaminationRun.case_pk == case.id)
            .order_by(ExaminationRun.run_number.desc())
            .limit(1)
            .options(selectinload(ExaminationRun.findings), selectinload(ExaminationRun.executions))
        )
        if run is None:
            case_reports.append({"case_id": case.case_id, "status": "NOT_EXAMINED"})
            continue
        runs.append(run)
        for finding in run.findings:
            findings.append(
                {
                    "id": finding.id,
                    "case_id": case.case_id,
                    "finding_type": finding.finding_type,
                    "rule_id": finding.rule_id,
                    "expected": finding.expected_json["comparison_value"],
                    "observed": finding.observed_json["comparison_value"],
                }
            )
        case_reports.append(
            {
                "case_id": case.case_id,
                "run_id": run.id,
                "run_number": run.run_number,
                "status": run.status,
                "ruleset_version": run.ruleset_version,
                "summary": run.summary_json,
                "incomplete_rules": [
                    {"rule_id": e.rule_id, "status": e.status, "reason": e.output_json["reason"]}
                    for e in run.executions
                    if e.status not in {"MATCH", "MISMATCH"}
                ],
            }
        )
    report = score_findings(references, findings)
    report.update(
        {
            "cases": case_reports,
            "raw_findings": findings,
            "rule_coverage": dict(Counter(e.rule_id for r in runs for e in r.executions)),
            "rule_results": dict(Counter(e.status for r in runs for e in r.executions)),
            "limitations": [
                "Five synthetic cases are not a production accuracy benchmark.",
                (
                    "Low-confidence or missing evidence remains incomplete and is counted "
                    "as a miss when a reference finding cannot be supported."
                ),
                (
                    "Duplicate-invoice financing risk is excluded; "
                    "no final decision accuracy is claimed."
                ),
            ],
        }
    )
    return report
