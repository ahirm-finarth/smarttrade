from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models.domain import Base, CaseParty, TradeCase
from app.services.demo_import import SourceError, ingest, prepare, read_sources

RAW = Path(__file__).resolve().parents[2] / "data/raw"


def test_workbook_csv_parity():
    csv = prepare(read_sources(RAW))
    workbook = prepare(read_sources(RAW / "Smart_Trade_Demo_Data.xlsx"))
    assert csv == workbook


def test_idempotency_and_non_demo_preservation():
    engine = create_engine("sqlite://")  # Isolated test only; runtime always uses MySQL.
    Base.metadata.create_all(engine)
    bundle = read_sources(RAW)
    with Session(engine) as session, session.begin():
        session.add(TradeCase(case_id="external-record", dataset_key=None))
    with Session(engine) as session, session.begin():
        counts = ingest(session, bundle)
        ids = session.execute(select(TradeCase.case_id, TradeCase.id)).all()
    with Session(engine) as session, session.begin():
        assert ingest(session, bundle) == counts
        assert session.execute(select(TradeCase.case_id, TradeCase.id)).all() == ids
        assert (
            session.scalar(select(func.count()).select_from(TradeCase))
            == len(bundle["trade_cases"]) + 1
        )
        assert session.scalar(select(func.count()).select_from(CaseParty)) == len(
            bundle["case_parties"]
        )
        case = session.scalar(
            select(TradeCase).where(TradeCase.case_id == bundle["trade_cases"][0]["case_id"])
        )
        assert case.priority is None and case.facility_id is None
        assert case.created_at.tzinfo is not None
        assert case.amount == Decimal(bundle["trade_cases"][0]["amount"])


def test_reject_orphans_and_bad_decimals_before_writes():
    bundle = read_sources(RAW)
    bundle["case_parties"][0]["case_id"] = "absent"
    with pytest.raises(SourceError, match="orphan"):
        prepare(bundle)
    bundle = read_sources(RAW)
    bundle["trade_cases"][0]["amount"] = "nan-invalid"
    with pytest.raises(SourceError, match="invalid data"):
        prepare(bundle)


def test_demo_cannot_overwrite_non_demo_case():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    bundle = read_sources(RAW)
    with Session(engine) as session, session.begin():
        session.add(TradeCase(case_id=bundle["trade_cases"][0]["case_id"], dataset_key=None))
    with Session(engine) as session, session.begin():
        with pytest.raises(SourceError, match="non-demo"):
            ingest(session, bundle)
