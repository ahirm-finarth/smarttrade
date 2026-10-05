import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.domain import TradeCase
from app.services.decision_engine import generate_decision


def main():
    parser = argparse.ArgumentParser(
        description="Generate deterministic decisions from operational DB cases"
    )
    parser.add_argument("--case-id")
    args = parser.parse_args()
    failed = 0
    with Session(get_engine()) as s:
        ids = s.scalars(select(TradeCase.case_id).order_by(TradeCase.case_id)).all()
    for id in ids:
        if args.case_id and args.case_id != id:
            continue
        try:
            with Session(get_engine()) as s:
                run = generate_decision(s, get_settings(), id)
                print(
                    (
                        f"{id}: {run.status} · {run.recommended_decision} · decision {run.id} · "
                        f"{run.workflow.state if run.workflow else 'No workflow'}"
                    ),
                    flush=True,
                )
                failed += run.status == "FAILED"
        except Exception:
            failed += 1
            print(f"{id}: FAILED (private diagnostics suppressed)", flush=True)
    if failed or (args.case_id and args.case_id not in ids):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
