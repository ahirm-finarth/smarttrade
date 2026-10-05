import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.domain import TradeCase
from app.services.risk_orchestration import run_risk_checks


def main():
    parser = argparse.ArgumentParser(
        description="Explicit deterministic risk runs using operational inputs"
    )
    parser.add_argument("--case-id")
    args = parser.parse_args()
    engine = get_engine()
    settings = get_settings()
    with Session(engine) as s:
        ids = s.scalars(select(TradeCase.case_id).order_by(TradeCase.case_id)).all()
    failed = 0
    for id in ids:
        if args.case_id and id != args.case_id:
            continue
        try:
            with Session(engine) as s:
                run = run_risk_checks(s, settings, id)
                print(f"{id}: {run.status} · run {run.run_number} · {run.summary_json}", flush=True)
                failed += run.status == "FAILED"
        except Exception:
            failed += 1
            print(f"{id}: FAILED (private diagnostics suppressed)", flush=True)
    if failed or (args.case_id and args.case_id not in ids):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
