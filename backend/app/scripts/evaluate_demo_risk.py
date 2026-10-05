import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.services.demo_risk_evaluation import evaluate_demo_risk


def main():
    parser = argparse.ArgumentParser(description="Offline evaluation of persisted risk findings")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with Session(get_engine()) as s:
            report = evaluate_demo_risk(s)
    except Exception:
        print("Risk evaluation failed; check reference fixtures and database availability.")
        raise SystemExit(1) from None
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n")
        args.output.with_suffix(".md").write_text(
            "# Synthetic risk evaluation\n\n"
            + "\n".join(
                f"{k}: {report[k]}"
                for k in (
                    "expected",
                    "detected",
                    "true_positives",
                    "false_positives",
                    "false_negatives",
                    "precision",
                    "recall",
                    "f1",
                )
            )
            + "\n\n"
            + report["scope"]
            + "\n\n"
            + "\n".join(report["limitations"])
            + "\n"
        )
    print(serialized)


if __name__ == "__main__":
    main()
