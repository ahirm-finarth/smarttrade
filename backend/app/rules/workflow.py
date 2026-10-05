"""Versioned deterministic queues and explicitly selectable demo identities."""

from enum import StrEnum

from app.integrations.risk.contracts import Category, SafeModel


class Role(StrEnum):
    MAKER = "TRADE_MAKER"
    CHECKER = "TRADE_CHECKER"
    TRADE = "TRADE_REVIEWER"
    COMPLIANCE = "TRADE_COMPLIANCE"
    LEGAL = "LEGAL_REVIEWER"
    SUPERVISOR = "SUPERVISOR"


class TaskType(StrEnum):
    MAKER = "MAKER_REVIEW"
    CHECKER = "CHECKER_APPROVAL"
    TRADE = "TRADE_REVIEW"
    COMPLIANCE = "COMPLIANCE_REVIEW"
    LEGAL = "LEGAL_REVIEW"
    INFORMATION = "REQUEST_INFORMATION"
    ESCALATION = "SUPERVISOR_ESCALATION"


class WorkflowState(StrEnum):
    MAKER = "AWAITING_MAKER"
    CHECKER = "AWAITING_CHECKER"
    SPECIALIST = "AWAITING_SPECIALIST"
    REFERRED = "REFERRED"
    INFORMATION = "NEEDS_INFORMATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


class Action(StrEnum):
    START = "START"
    SUBMIT = "SUBMIT_FOR_CHECKER"
    APPROVE = "APPROVE"
    RETURN = "RETURN_TO_MAKER"
    REFER = "REFER"
    REJECT = "REJECT"
    CLEAR = "CONFIRM_CLEAR"
    ISSUE = "CONFIRM_ISSUE"
    INFORMATION = "REQUEST_INFORMATION"
    PROVIDED = "INFORMATION_PROVIDED"
    ESCALATE = "ESCALATE"
    ACKNOWLEDGE_BLOCK = "ACKNOWLEDGE_BLOCK"


class EventType(StrEnum):
    DECISION = "DECISION_GENERATED"
    SUPERSEDED = "DECISION_SUPERSEDED"
    TASK = "TASK_CREATED"
    CANCEL = "TASK_CANCELLED"
    START = "TASK_STARTED"
    MAKER = "MAKER_SUBMITTED"
    APPROVE = "CHECKER_APPROVED"
    RETURN = "CHECKER_RETURNED"
    CLEAR = "SPECIALIST_CLEARED"
    ISSUE = "SPECIALIST_CONFIRMED_ISSUE"
    INFORMATION = "INFORMATION_REQUESTED"
    PROVIDED = "INFORMATION_PROVIDED"
    ESCALATE = "SUPERVISOR_ESCALATED"
    REFER = "CASE_REFERRED"
    BLOCK = "CASE_BLOCKED"
    PASS = "FINAL_PASS"
    REJECT = "FINAL_REJECT"
    OVERRIDE = "OVERRIDE_APPLIED"
    ADVISORY = "EXCEPTION_SUMMARY_GENERATED"


TASK_ROLES = {
    TaskType.MAKER: Role.MAKER,
    TaskType.CHECKER: Role.CHECKER,
    TaskType.TRADE: Role.TRADE,
    TaskType.COMPLIANCE: Role.COMPLIANCE,
    TaskType.LEGAL: Role.LEGAL,
    TaskType.INFORMATION: Role.MAKER,
    TaskType.ESCALATION: Role.SUPERVISOR,
}
SPECIALIST_TASKS = {TaskType.TRADE, TaskType.COMPLIANCE, TaskType.LEGAL}


class RoutingPolicy(SafeModel):
    version: str = "routing-v1"
    category_routes: dict[Category, TaskType] = {
        Category.SCREENING: TaskType.COMPLIANCE,
        Category.COUNTRY: TaskType.COMPLIANCE,
        Category.PORT: TaskType.COMPLIANCE,
        Category.VESSEL: TaskType.COMPLIANCE,
        Category.DUPLICATE: TaskType.TRADE,
        Category.GOODS: TaskType.COMPLIANCE,
        Category.FAIR_VALUE: TaskType.TRADE,
    }


ROUTING = RoutingPolicy()


def route_reason(reason, playbook, policy=ROUTING):
    if reason["impact"] == "INFO":
        return None
    if reason["impact"] == "BLOCK":
        return TaskType.ESCALATION
    evidence = reason["evidence_json"]
    if reason["reason_type"] in {"DOCUMENTARY_FINDING", "INCOMPLETE_EXAMINATION"}:
        return TaskType.LEGAL if playbook == "Performance Guarantee" else TaskType.TRADE
    category = evidence.get("category", evidence.get("provider_type"))
    if category in policy.category_routes:
        return policy.category_routes[category]
    if evidence.get("source") == "risk":
        return TaskType.COMPLIANCE
    return TaskType.TRADE


class DemoActor(SafeModel):
    actor_id: str
    display_name: str
    roles: tuple[Role, ...]


ACTORS = {
    id: DemoActor(actor_id=id, display_name=label, roles=roles)
    for id, label, roles in (
        ("maker.demo", "Trade Maker", (Role.MAKER,)),
        ("checker.demo", "Trade Checker", (Role.CHECKER,)),
        ("trade.demo", "Trade Reviewer", (Role.TRADE,)),
        ("compliance.demo", "Compliance Reviewer", (Role.COMPLIANCE,)),
        ("legal.demo", "Legal Reviewer", (Role.LEGAL,)),
        ("supervisor.demo", "Supervisor", (Role.SUPERVISOR,)),
        ("dual.demo", "Dual-role Demo User (SoD demonstration)", (Role.MAKER, Role.CHECKER)),
    )
}
