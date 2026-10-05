import pytest

from app.rules.workflow import ACTORS, ROUTING, TASK_ROLES, Role, TaskType, route_reason


@pytest.mark.parametrize(
    "category,queue",
    [
        ("screening", TaskType.COMPLIANCE),
        ("country", TaskType.COMPLIANCE),
        ("port", TaskType.COMPLIANCE),
        ("vessel", TaskType.COMPLIANCE),
        ("goods", TaskType.COMPLIANCE),
        ("duplicate", TaskType.TRADE),
        ("fair_value", TaskType.TRADE),
    ],
)
def test_versioned_category_routing(category, queue):
    reason = {
        "impact": "REFER",
        "reason_type": "RISK_FINDING",
        "evidence_json": {"category": category},
    }
    assert route_reason(reason, "Import LC") == queue
    assert ROUTING.version == "routing-v1"
    assert TASK_ROLES[queue]


def test_documentary_guarantee_and_hard_block_queues_are_distinct():
    reason = {"impact": "REFER", "reason_type": "INCOMPLETE_EXAMINATION", "evidence_json": {}}
    assert route_reason(reason, "Import LC") == TaskType.TRADE
    assert route_reason(reason, "Performance Guarantee") == TaskType.LEGAL
    assert route_reason({**reason, "impact": "BLOCK"}, "Import LC") == TaskType.ESCALATION
    assert route_reason({**reason, "impact": "INFO"}, "Import LC") is None


def test_demo_actor_ids_are_stable_and_dual_role_identity_is_one_person():
    assert ACTORS["maker.demo"].roles == (Role.MAKER,)
    assert ACTORS["dual.demo"].roles == (Role.MAKER, Role.CHECKER)
    assert ACTORS["dual.demo"].actor_id == "dual.demo"
