from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, make_url

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", extra="ignore", case_sensitive=False, hide_input_in_errors=True
    )

    database_url: SecretStr | None = None
    mysql_host: str | None = Field(None, validation_alias=AliasChoices("MYSQL_HOST", "DB_HOST"))
    mysql_port: int = Field(3306, validation_alias=AliasChoices("MYSQL_PORT", "DB_PORT"))
    mysql_user: str | None = Field(None, validation_alias=AliasChoices("MYSQL_USER", "DB_USER"))
    mysql_password: SecretStr | None = Field(
        None, validation_alias=AliasChoices("MYSQL_PASSWORD", "DB_PASSWORD")
    )
    mysql_database: str | None = Field(
        None, validation_alias=AliasChoices("MYSQL_DATABASE", "DB_NAME")
    )
    llm_api_url: str | None = None
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    llm_protocol: str = "unconfigured"
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("database_url", "mysql_password", "llm_api_key", mode="before")
    @classmethod
    def blank_secret(cls, value):
        return value or None

    @property
    def sqlalchemy_url(self) -> URL:
        if self.database_url:
            try:
                url = make_url(self.database_url.get_secret_value())
            except Exception:
                raise ValueError("DATABASE_URL must be a valid MySQL URL") from None
            if url.get_backend_name() == "mysql":
                return url.set(drivername="mysql+pymysql").update_query_dict({"charset": "utf8mb4"})
        if not all([self.mysql_host, self.mysql_user, self.mysql_database]):
            raise ValueError("MySQL configuration is incomplete")
        return URL.create(
            "mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password.get_secret_value() if self.mysql_password else None,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_url and self.llm_model and self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
