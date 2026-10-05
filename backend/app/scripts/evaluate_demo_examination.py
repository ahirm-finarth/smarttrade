import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.services.demo_examination_evaluation import evaluate_demo_examination


def main():
    parser = argparse.ArgumentParser(
        description="Offline evaluation of stored documentary findings against synthetic labels"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with Session(get_engine()) as session:
            report = evaluate_demo_examination(session)
    except Exception:
        print("Evaluation failed; check migration, reference fixtures and database connection.")
        raise SystemExit(1) from None
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n")
        args.output.with_suffix(".md").write_text(
            "# Documentary examination evaluation\n\n"
            f"Expected: {report['expected_discrepancies']}; "
            f"raw findings: {report['detected_raw_findings']}; "
            f"detected families: {report['detected_case_families']}.\n\n"
            f"TP {report['true_positives']} · FP {report['false_positives']} "
            f"· FN {report['false_negatives']}\n\n"
            f"Precision {report['precision']} · Recall {report['recall']} · F1 {report['f1']}\n\n"
            + "\n".join(f"- {c['case_id']}: {c['status']}" for c in report["cases"])
            + "\n\n"
            + report["unit"]
            + ".\n\n"
            + "\n".join(report["limitations"])
            + "\n"
        )
    print(serialized)


if __name__ == "__main__":
    main()
