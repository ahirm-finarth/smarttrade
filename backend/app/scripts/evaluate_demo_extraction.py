import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.services.demo_evaluation import evaluate_demo_extraction


def main():
    parser = argparse.ArgumentParser(
        description="Compare PDF-derived facts with labelled demo CSVs"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with Session(get_engine()) as session:
            report = evaluate_demo_extraction(session)
    except Exception:
        print("Evaluation failed; check migration, reference fixtures, and database connection.")
        raise SystemExit(1) from None
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n")
    print(serialized)


if __name__ == "__main__":
    main()
