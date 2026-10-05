"""Explicit examination runner; operational DB cases only, no labelled fixtures."""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.domain import TradeCase
from app.services.examination_engine import run_examination


def main():
    parser = argparse.ArgumentParser(
        description="Examine current source-derived facts; each invocation creates new stored runs"
    )
    parser.add_argument("--case-id")
    args = parser.parse_args()
    engine, settings = get_engine(), get_settings()
    with Session(engine) as session:
        ids = session.scalars(select(TradeCase.case_id).order_by(TradeCase.case_id)).all()
    failures = 0
    for case_id in ids:
        if args.case_id and args.case_id != case_id:
            continue
        try:
            with Session(engine) as session:
                run = run_examination(session, settings, case_id)
                print(
                    f"{case_id}: {run.status} · run {run.run_number} · {run.summary_json}",
                    flush=True,
                )
                failures += run.status == "FAILED"
        except Exception:
            failures += 1
            print(f"{case_id}: examination failed (connection details suppressed)", flush=True)
    if args.case_id and args.case_id not in ids:
        print("Case not found")
        raise SystemExit(1)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
