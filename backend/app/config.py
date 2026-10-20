from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, computed_field, field_validator, model_validator
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
    app_version: str = Field(default="0.9.0", validation_alias="APP_VERSION")
    database_url: str = Field(
        default=f"sqlite:///{BACKEND_ROOT / 'railops.db'}", validation_alias="DATABASE_URL"
    )
    backend_cors_origins: str = Field(
        default="http://localhost:3000", validation_alias="BACKEND_CORS_ORIGINS"
    )
    max_request_body_bytes: int = Field(
        default=1_048_576,
        ge=1_024,
        le=10_485_760,
        validation_alias="MAX_REQUEST_BODY_BYTES",
    )
    database_pool_size: int = Field(
        default=5, ge=1, le=20, validation_alias="DATABASE_POOL_SIZE"
    )
    database_max_overflow: int = Field(
        default=5, ge=0, le=20, validation_alias="DATABASE_MAX_OVERFLOW"
    )
    database_pool_timeout_seconds: int = Field(
        default=10, ge=1, le=60, validation_alias="DATABASE_POOL_TIMEOUT_SECONDS"
    )
    database_pool_recycle_seconds: int = Field(
        default=300, ge=30, le=3_600, validation_alias="DATABASE_POOL_RECYCLE_SECONDS"
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

    @model_validator(mode="after")
    def validate_production_database(self) -> "Settings":
        if self.app_env == "production":
            database_url = make_url(self.database_url)
            if database_url.get_backend_name() != "postgresql":
                raise ValueError("Production requires a PostgreSQL DATABASE_URL.")
            ssl_mode = database_url.query.get("sslmode", "").lower()
            if ssl_mode not in {"require", "verify-ca", "verify-full"}:
                raise ValueError(
                    "Production PostgreSQL connections require sslmode=require, "
                    "verify-ca, or verify-full."
                )
        return self

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
        if self.app_env == "production" and not origins:
            raise ValueError("At least one production CORS origin is required.")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(f"CORS origin must be an exact HTTP(S) origin: {origin}.")
            if self.app_env == "production" and parsed.scheme != "https":
                raise ValueError("Production CORS origins must use HTTPS.")
        return [origin.rstrip("/") for origin in origins]


@lru_cache
def get_settings() -> Settings:
    return Settings()

