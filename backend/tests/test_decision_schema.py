from app.models import Base


def test_governed_decision_schema_is_additive_owned_and_indexed():
    names = {
        "smart_trade_decision_runs",
        "smart_trade_decision_reasons",
        "smart_trade_governed_workflows",
        "smart_trade_workflow_tasks",
        "smart_trade_workflow_events",
        "smart_trade_decision_overrides",
        "smart_trade_finding_resolutions",
    }
    assert names.issubset(Base.metadata.tables)
    assert "smart_trade_approval_events" in Base.metadata.tables
    for name in names:
        table = Base.metadata.tables[name]
        assert table.foreign_keys and table.indexes
        assert table.kwargs["mysql_charset"] == "utf8mb4"
    decision = Base.metadata.tables["smart_trade_decision_runs"]
    assert "final_outcome" not in decision.c
    assert "expected_decision" not in decision.c
    assert "final_outcome" in Base.metadata.tables["smart_trade_governed_workflows"].c
