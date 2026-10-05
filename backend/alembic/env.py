from alembic import context
from app.db.session import get_engine
from app.models import Base


def include_name(name, type_, parent_names):
    if type_ == "table":
        return name in Base.metadata.tables
    return True


def configure(connection=None, url=None):
    context.configure(
        connection=connection,
        url=url,
        target_metadata=Base.metadata,
        include_name=include_name,
        version_table="smart_trade_alembic_version",
        compare_type=True,
        literal_binds=connection is None,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    from app.core.config import get_settings

    configure(url=get_settings().sqlalchemy_url)
else:
    with get_engine().connect() as connection:
        configure(connection=connection)
