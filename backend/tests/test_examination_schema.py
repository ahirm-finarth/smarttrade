from sqlalchemy import create_engine, inspect

from app.models import Base


def test_examination_tables_are_separate_and_indexed():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = {
        "smart_trade_examination_runs",
        "smart_trade_rule_executions",
        "smart_trade_fact_relations",
        "smart_trade_detected_discrepancies",
    }
    assert tables.issubset(inspector.get_table_names())
    assert "smart_trade_discrepancies" in inspector.get_table_names()
    for table in tables:
        assert inspector.get_foreign_keys(table)
        assert inspector.get_indexes(table)
        assert inspector.get_unique_constraints(table)
    engine.dispose()
