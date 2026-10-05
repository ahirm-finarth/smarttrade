"""initial Smart Trade source-grounded schema"""

import sqlalchemy as sa

from alembic import op

revision = "30af12917573"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smart_trade_cases",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_key", sa.String(length=64), nullable=True),
        sa.Column("scenario", sa.String(length=160), nullable=True),
        sa.Column("product_playbook", sa.String(length=100), nullable=True),
        sa.Column("direction", sa.String(length=32), nullable=True),
        sa.Column("applicant", sa.String(length=200), nullable=True),
        sa.Column("beneficiary", sa.String(length=200), nullable=True),
        sa.Column("customer_id", sa.String(length=64), nullable=True),
        sa.Column("facility_id", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("priority", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=160), nullable=True),
        sa.Column("expected_decision", sa.String(length=16), nullable=True),
        sa.Column("demo_narrative", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_cases_dataset_key"), "smart_trade_cases", ["dataset_key"], unique=False
    )
    op.create_index(
        op.f("ix_smart_trade_cases_expected_decision"),
        "smart_trade_cases",
        ["expected_decision"],
        unique=False,
    )
    op.create_index(
        op.f("ix_smart_trade_cases_product_playbook"),
        "smart_trade_cases",
        ["product_playbook"],
        unique=False,
    )
    op.create_table(
        "smart_trade_demo_risk_rules",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_key", sa.String(length=64), nullable=False),
        sa.Column("playbook", sa.String(length=100), nullable=True),
        sa.Column("control_type", sa.String(length=64), nullable=True),
        sa.Column("logic", sa.Text(), nullable=True),
        sa.Column("default_route", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_demo_risk_rules_dataset_key"),
        "smart_trade_demo_risk_rules",
        ["dataset_key"],
        unique=False,
    )
    op.create_table(
        "smart_trade_demo_screening_references",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_key", sa.String(length=64), nullable=False),
        sa.Column("reference_type", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_demo_screening_references_dataset_key"),
        "smart_trade_demo_screening_references",
        ["dataset_key"],
        unique=False,
    )
    op.create_table(
        "smart_trade_approval_events",
        sa.Column("event_time", sa.DateTime(), nullable=True),
        sa.Column("actor_role", sa.String(length=100), nullable=True),
        sa.Column("actor_id", sa.String(length=100), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("case_pk", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_pk"],
            ["smart_trade_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_pk", "source_key"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_approval_events_case_pk"),
        "smart_trade_approval_events",
        ["case_pk"],
        unique=False,
    )
    op.create_table(
        "smart_trade_case_documents",
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("expected", sa.Boolean(), nullable=True),
        sa.Column("received", sa.Boolean(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("case_pk", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_pk"],
            ["smart_trade_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_pk", "source_key"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_case_documents_case_pk"),
        "smart_trade_case_documents",
        ["case_pk"],
        unique=False,
    )
    op.create_table(
        "smart_trade_case_parties",
        sa.Column("party_role", sa.String(length=64), nullable=True),
        sa.Column("party_name", sa.String(length=200), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("screening_status", sa.String(length=32), nullable=True),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("case_pk", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_pk"],
            ["smart_trade_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_pk", "source_key"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_case_parties_case_pk"),
        "smart_trade_case_parties",
        ["case_pk"],
        unique=False,
    )
    op.create_table(
        "smart_trade_discrepancies",
        sa.Column("finding_id", sa.String(length=64), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("rule_id", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("field", sa.String(length=100), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("observed_value", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("route_to", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("case_pk", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_pk"],
            ["smart_trade_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_pk", "source_key"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_discrepancies_case_pk"),
        "smart_trade_discrepancies",
        ["case_pk"],
        unique=False,
    )
    op.create_table(
        "smart_trade_risk_events",
        sa.Column("risk_id", sa.String(length=64), nullable=True),
        sa.Column("risk_type", sa.String(length=100), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("case_pk", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_pk"],
            ["smart_trade_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_pk", "source_key"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_risk_events_case_pk"),
        "smart_trade_risk_events",
        ["case_pk"],
        unique=False,
    )
    op.create_table(
        "smart_trade_trade_lines",
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("item_no", sa.Integer(), nullable=True),
        sa.Column("goods_description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("uom", sa.String(length=32), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("line_amount", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("case_pk", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_pk"],
            ["smart_trade_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_pk", "source_key"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_smart_trade_trade_lines_case_pk"),
        "smart_trade_trade_lines",
        ["case_pk"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_smart_trade_trade_lines_case_pk"), table_name="smart_trade_trade_lines")
    op.drop_table("smart_trade_trade_lines")
    op.drop_index(op.f("ix_smart_trade_risk_events_case_pk"), table_name="smart_trade_risk_events")
    op.drop_table("smart_trade_risk_events")
    op.drop_index(
        op.f("ix_smart_trade_discrepancies_case_pk"), table_name="smart_trade_discrepancies"
    )
    op.drop_table("smart_trade_discrepancies")
    op.drop_index(
        op.f("ix_smart_trade_case_parties_case_pk"), table_name="smart_trade_case_parties"
    )
    op.drop_table("smart_trade_case_parties")
    op.drop_index(
        op.f("ix_smart_trade_case_documents_case_pk"), table_name="smart_trade_case_documents"
    )
    op.drop_table("smart_trade_case_documents")
    op.drop_index(
        op.f("ix_smart_trade_approval_events_case_pk"), table_name="smart_trade_approval_events"
    )
    op.drop_table("smart_trade_approval_events")
    op.drop_index(
        op.f("ix_smart_trade_demo_screening_references_dataset_key"),
        table_name="smart_trade_demo_screening_references",
    )
    op.drop_table("smart_trade_demo_screening_references")
    op.drop_index(
        op.f("ix_smart_trade_demo_risk_rules_dataset_key"), table_name="smart_trade_demo_risk_rules"
    )
    op.drop_table("smart_trade_demo_risk_rules")
    op.drop_index(op.f("ix_smart_trade_cases_product_playbook"), table_name="smart_trade_cases")
    op.drop_index(op.f("ix_smart_trade_cases_expected_decision"), table_name="smart_trade_cases")
    op.drop_index(op.f("ix_smart_trade_cases_dataset_key"), table_name="smart_trade_cases")
    op.drop_table("smart_trade_cases")
