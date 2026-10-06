import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.services.demo_decision_evaluation import evaluate_demo_decisions


def main():
    parser = argparse.ArgumentParser(
        description="Offline evaluation of saved system recommendations"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with Session(get_engine()) as session:
            report = evaluate_demo_decisions(session)
    except Exception:
        print("Evaluation unavailable; check the database and generated decisions.")
        raise SystemExit(1) from None
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n")
    print(serialized)


if __name__ == "__main__":
    main()
