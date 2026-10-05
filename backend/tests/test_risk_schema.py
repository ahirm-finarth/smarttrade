from app.models import Base


def test_risk_tables_are_separate_indexed_and_auditable():
    for name in ("risk_runs", "provider_checks", "risk_rule_executions", "detected_risk_findings"):
        table = Base.metadata.tables["smart_trade_" + name]
        assert table.foreign_keys and table.indexes
        assert any(c.__class__.__name__ == "UniqueConstraint" for c in table.constraints)
    assert "smart_trade_risk_events" in Base.metadata.tables
    assert "smart_trade_rule_executions" in Base.metadata.tables
