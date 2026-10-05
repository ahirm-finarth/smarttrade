from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine():
    return create_engine(
        get_settings().sqlalchemy_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        hide_parameters=True,
        connect_args={"connect_timeout": 10},
    )


def database_connected() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_session():
    with Session(get_engine()) as session:
        yield session
