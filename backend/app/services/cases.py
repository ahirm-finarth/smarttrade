from app.repositories.cases import CaseRepository
from app.schemas.cases import CaseDetail, CaseList, CaseSummary, DashboardSummary, ProductCount
from app.services.demo_import import DATASET_KEY


class CaseNotFound(Exception):
    pass


class CaseService:
    def __init__(self, repository: CaseRepository):
        self.repository = repository

    def list(self, limit=50, offset=0, q=None, product=None, outcome=None):
        rows, total = self.repository.list(limit, offset, q, product, outcome)
        return CaseList(
            items=[
                CaseSummary.model_validate(row).model_copy(
                    update={
                        "is_synthetic": row.dataset_key == DATASET_KEY,
                    }
                )
                for row in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def detail(self, case_id):
        row = self.repository.detail(case_id)
        if row is None:
            raise CaseNotFound
        return CaseDetail.model_validate(row).model_copy(
            update={
                "is_synthetic": row.dataset_key == DATASET_KEY,
            }
        )

    def summary(self):
        total, synthetic, outcomes, products = self.repository.summary()
        counts = {"PASS": 0, "REFER": 0, "BLOCK": 0}
        counts.update({name or "UNSPECIFIED": count for name, count in outcomes})
        return DashboardSummary(
            total_cases=total,
            synthetic_cases=synthetic,
            expected_outcomes=counts,
            product_distribution=[
                ProductCount(product=name, count=count) for name, count in products
            ],
        )
