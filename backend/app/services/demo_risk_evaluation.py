"""Offline evaluation only. Never imported by risk orchestration/providers."""

import csv
from collections import Counter
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import CaseParty, TradeCase
from app.models.risk import RiskRun
from app.services.comparisons import normalized_party, normalized_text

ROOT = Path(__file__).resolve().parents[3] / "data/raw"


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def score(expected, detected):
    matches = []
    misses = []
    accounted = set()
    for label in expected:
        hits = [
            f
            for f in detected
            if f["case_id"] == label["case_id"]
            and f["category"] == label["category"]
            and (
                label.get("subject") is None
                or normalized_text(f["subject"]) == normalized_text(label["subject"])
            )
        ]
        if hits:
            matches.append({**label, "finding_ids": [f["id"] for f in hits]})
            accounted.update(f["id"] for f in hits)
        else:
            misses.append(label)
    extra = [f for f in detected if f["id"] not in accounted]
    tp, fp, fn = len(matches), len(extra), len(misses)
    precision = Decimal(tp) / Decimal(tp + fp) if tp + fp else Decimal(0)
    recall = Decimal(tp) / Decimal(tp + fn) if tp + fn else Decimal(0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else Decimal(0)
    return {
        "expected": len(expected),
        "detected": len(detected),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": str(precision.quantize(Decimal(".0001"))),
        "recall": str(recall.quantize(Decimal(".0001"))),
        "f1": str(f1.quantize(Decimal(".0001"))),
        "matched": matches,
        "missed": misses,
        "unmatched_findings": extra,
    }


def evaluate_demo_risk(session: Session):
    cases = session.scalars(select(TradeCase).order_by(TradeCase.case_id)).all()
    expected = []
    excluded = []
    clear_cases = []
    for event in read(ROOT / "risk_events.csv"):
        category = {
            "Country/port policy": "port",
            "Vessel screening": "vessel",
            "Fair value": "fair_value",
        }.get(event["risk_type"])
        if category:
            expected.append(
                {
                    "reference_id": event["risk_id"],
                    "case_id": event["case_id"],
                    "category": category,
                    "subject": event["subject"],
                    "testability": "No supplied price band; counted as a miss"
                    if category == "fair_value"
                    else "Source and mock reference available",
                }
            )
        elif event["result"] == "CLEAR":
            clear_cases.append(event["case_id"])
        else:
            excluded.append(
                {
                    "reference_id": event["risk_id"],
                    "reason": "Post-event export monitoring is deferred"
                    if event["risk_type"] == "Export realisation watch"
                    else (
                        "Guarantee documentary condition belongs to Phase 3; not duplicated as risk"
                    ),
                }
            )
    parties = session.scalars(select(CaseParty)).all()
    for reference in read(ROOT / "reference_screening.csv"):
        if reference["reference_type"] != "Fictional counterparty":
            continue
        matched_cases = {
            p.case_pk
            for p in parties
            if p.party_name
            and normalized_party(p.party_name) == normalized_party(reference["name"])
        }
        for case in cases:
            if case.id in matched_cases:
                expected.append(
                    {
                        "reference_id": reference["reference_id"],
                        "case_id": case.case_id,
                        "category": "screening",
                        "subject": reference["name"],
                        "testability": "Actual operational party and independent mock reference",
                    }
                )
    for label in read(ROOT / "discrepancies.csv"):
        if label["rule_id"] == "DOC-INV-REF-001":
            expected.append(
                {
                    "reference_id": label["finding_id"],
                    "case_id": label["case_id"],
                    "category": "duplicate",
                    "subject": None,
                    "testability": (
                        "Historical labelled invoice is not present as a stored candidate; "
                        "counted as a miss"
                    ),
                }
            )
    detected = []
    reports = []
    for case in cases:
        run = session.scalar(
            select(RiskRun)
            .where(RiskRun.case_pk == case.id)
            .order_by(RiskRun.run_number.desc())
            .limit(1)
            .options(selectinload(RiskRun.findings), selectinload(RiskRun.checks))
        )
        if not run:
            reports.append({"case_id": case.case_id, "status": "NOT_RUN"})
            continue
        for finding in run.findings:
            detected.append(
                {
                    "id": finding.id,
                    "case_id": case.case_id,
                    "category": finding.category,
                    "subject": finding.evidence_json["subject"]["subject"],
                    "finding_type": finding.finding_type,
                    "rule_id": finding.rule_id,
                }
            )
        reports.append(
            {
                "case_id": case.case_id,
                "run_id": run.id,
                "run_number": run.run_number,
                "status": run.status,
                "summary": run.summary_json,
                "unchecked_or_incomplete": [
                    {
                        "category": c.provider_type,
                        "status": c.status,
                        "reason": c.result_json["reason"],
                    }
                    for c in run.checks
                    if c.status
                    in {"NOT_CHECKED", "NOT_APPLICABLE", "INSUFFICIENT_DATA", "PROVIDER_ERROR"}
                ],
            }
        )
    result = score(expected, detected)
    result.update(
        {
            "scope": "All in-scope labelled positives, including missing benchmark/history inputs",
            "cases": reports,
            "excluded": excluded,
            "raw_findings": detected,
            "clear_case_false_material_findings": {
                id: sum(f["case_id"] == id for f in detected) for id in clear_cases
            },
            "category_metrics": {
                category: score(
                    [e for e in expected if e["category"] == category],
                    [f for f in detected if f["category"] == category],
                )
                for category in (
                    "screening",
                    "country",
                    "port",
                    "vessel",
                    "duplicate",
                    "goods",
                    "fair_value",
                )
            },
            "findings_by_category": dict(Counter(f["category"] for f in detected)),
            "limitations": [
                "Synthetic references are not genuine sanctions or geopolitical claims.",
                "No price band was invented to replay the fair-value label.",
                "No historical invoice or financing event was fabricated for duplicate detection.",
                (
                    "Missing applicable positive inputs are included as false negatives "
                    "in the primary metric."
                ),
                "Five synthetic cases are not a production accuracy benchmark.",
            ],
        }
    )
    return result
