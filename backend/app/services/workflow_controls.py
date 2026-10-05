"""Server-owned demo roles and segregation of duties; not production IAM."""

from app.rules.workflow import ACTORS, EventType


class WorkflowForbidden(Exception):
    pass


class WorkflowConflict(Exception):
    pass


def demo_actor(id):
    actor = ACTORS.get(id)
    if actor is None:
        raise WorkflowForbidden("Unknown demo identity")
    return actor


def authorize(actor, role):
    if role not in actor.roles:
        raise WorkflowForbidden("Demo actor does not hold the task's required role")


def maker_actor_ids(run):
    return {e.actor_id for e in run.events if e.event_type == EventType.MAKER}


def enforce_sod(run, actor):
    if actor.actor_id in maker_actor_ids(run):
        raise WorkflowForbidden(
            "Segregation of duties: a maker cannot check the same governed decision"
        )
