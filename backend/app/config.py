from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Environment-backed runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_name: str = Field(default="RailOps AI API", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    database_url: str = Field(
        default=f"sqlite:///{BACKEND_ROOT / 'railops.db'}", validation_alias="DATABASE_URL"
    )
    backend_cors_origins: str = Field(
        default="http://localhost:3000", validation_alias="BACKEND_CORS_ORIGINS"
    )

    @field_validator("app_env")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        environment = value.strip().lower()
        if environment not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production.")
        return environment

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        database_url = value.strip()
        if not database_url:
            raise ValueError("DATABASE_URL must not be blank.")
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if database_url.startswith("sqlite"):
            url = make_url(database_url)
            if url.database and url.database != ":memory:":
                database_path = Path(url.database).expanduser()
                if not database_path.is_absolute():
                    database_path = (BACKEND_ROOT / database_path).resolve()
                return url.set(database=str(database_path)).render_as_string(hide_password=False)
        return database_url

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        origins = [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]
        if self.app_env == "production" and "*" in origins:
            raise ValueError("Unrestricted CORS is not allowed in production.")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()

