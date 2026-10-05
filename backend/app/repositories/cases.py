from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import TradeCase
from app.services.demo_import import DATASET_KEY


class CaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def list(
        self, limit: int, offset: int, q: str | None, product: str | None, outcome: str | None
    ):
        statement = select(TradeCase)
        if q:
            pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            statement = statement.where(
                or_(
                    TradeCase.case_id.ilike(pattern, escape="\\"),
                    TradeCase.applicant.ilike(pattern, escape="\\"),
                    TradeCase.beneficiary.ilike(pattern, escape="\\"),
                )
            )
        if product:
            statement = statement.where(TradeCase.product_playbook == product)
        if outcome:
            statement = statement.where(TradeCase.expected_decision == outcome)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = self.session.scalars(
            statement.order_by(TradeCase.case_id).limit(limit).offset(offset)
        )
        return list(rows), total

    def detail(self, case_id: str):
        return self.session.scalar(
            select(TradeCase)
            .where(TradeCase.case_id == case_id)
            .options(
                selectinload(TradeCase.parties),
                selectinload(TradeCase.documents),
                selectinload(TradeCase.trade_lines),
                selectinload(TradeCase.discrepancies),
                selectinload(TradeCase.risk_events),
                selectinload(TradeCase.approvals),
            )
        )

    def summary(self):
        total = self.session.scalar(select(func.count()).select_from(TradeCase))
        synthetic = self.session.scalar(
            select(func.count())
            .select_from(TradeCase)
            .where(
                TradeCase.dataset_key == DATASET_KEY,
            )
        )
        outcomes = self.session.execute(
            select(
                TradeCase.expected_decision,
                func.count(),
            ).group_by(TradeCase.expected_decision)
        ).all()
        products = self.session.execute(
            select(
                TradeCase.product_playbook,
                func.count(),
            )
            .group_by(TradeCase.product_playbook)
            .order_by(TradeCase.product_playbook)
        ).all()
        return total, synthetic, outcomes, products
