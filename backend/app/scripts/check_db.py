"""Read-only database inspection without hostnames, credentials, or unrelated table names."""

from sqlalchemy import inspect

from app.db.session import database_connected, get_engine
from app.models import Base


def main():
    if not database_connected():
        print("MySQL unavailable; verify configuration and network access.")
        raise SystemExit(1)
    try:
        tables = set(inspect(get_engine()).get_table_names())
    except Exception:
        print("MySQL connected; schema inspection unavailable.")
        raise SystemExit(1) from None
    owned = set(Base.metadata.tables) | {"smart_trade_alembic_version"}
    print("MySQL connected")
    print(f"Unrelated tables (untouched): {len(tables - owned)}")
    print("Smart Trade tables present:")
    for table in sorted(tables & owned):
        print(table)
    missing = owned - tables
    if missing:
        print(f"Pending Smart Trade tables: {len(missing)}; run make migrate.")


if __name__ == "__main__":
    main()
