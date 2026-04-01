import warnings
from enum import StrEnum

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a .env file.

    All fields without a default are **required** — the application will not
    start if they are missing, which prevents silent misconfiguration.

    Set APP_ENV=production to enable strict TLS validation and enforce that
    all security-sensitive fields are present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Runtime environment. Use 'production' for live deployments.",
    )

    # Flask
    flask_secret_key: str = Field(
        ...,
        description="Secret key used by Flask to sign sessions and CSRF tokens.",
    )

    # Elasticsearch
    elastic_host: str = Field(
        default="https://127.0.0.1:9200",
        description="Full URL of the Elasticsearch node.",
    )
    elastic_user: str = Field(
        default="elastic",
        description="Elasticsearch username for basic authentication.",
    )
    elastic_password: str = Field(
        ...,
        description="Elasticsearch password for basic authentication.",
    )
    elastic_cert_fingerprint: str | None = Field(
        default=None,
        description=(
            "SHA-256 fingerprint of the Elasticsearch TLS certificate. "
            "Required in production. In development, TLS verification is skipped when absent. "
            "Obtain it with: openssl s_client -connect <host>:9200 </dev/null 2>/dev/null "
            "| openssl x509 -noout -fingerprint -sha256"
        ),
    )

    # ── Connection pool tuning ─────────────────────────────────────────────────
    # These have safe defaults for development. Tune for production based on
    # expected concurrency and the number of Elasticsearch nodes.

    elastic_connections_per_node: int = Field(
        default=10,
        ge=1,
        description=(
            "Maximum number of simultaneous HTTP connections per Elasticsearch node. "
            "Increase for high-concurrency production deployments."
        ),
    )
    elastic_request_timeout: float = Field(
        default=10.0,
        gt=0,
        description=(
            "Seconds to wait for an Elasticsearch response before raising a timeout error. "
            "Lower in production to fail fast; raise for bulk indexing workloads."
        ),
    )
    elastic_max_retries: int = Field(
        default=3,
        ge=0,
        description=(
            "Number of times the client retries a failed request before raising. "
            "Set to 0 to disable retries."
        ),
    )

    # ── Upload ────────────────────────────────────────────────────────────────

    max_upload_mb: int = Field(
        default=50,
        ge=1,
        description="Maximum upload file size in megabytes. Enforced by Flask before the view runs.",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────

    allowed_origins: list[str] = Field(
        default=["*"],
        description=(
            "Allowed CORS origins. Set via JSON env var: "
            'ALLOWED_ORIGINS=\'[\"https://logpyre.example.com\"]\'. '
            "Use \"[\"*\"]\" in development only — rejected in production."
        ),
    )

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        """Enforce stricter requirements when running in production."""
        if self.app_env == Environment.PRODUCTION:
            if not self.elastic_cert_fingerprint:
                raise ValueError(
                    "ELASTIC_CERT_FINGERPRINT is required in production."
                )
            if self.flask_secret_key == "dev-only-insecure-key":
                raise ValueError(
                    "FLASK_SECRET_KEY must be changed from the default in production."
                )
            if self.allowed_origins == ["*"]:
                raise ValueError(
                    "ALLOWED_ORIGINS must be restricted to specific domains in production."
                )
        else:
            if not self.elastic_cert_fingerprint:
                warnings.warn(
                    "ELASTIC_CERT_FINGERPRINT is not set — TLS verification is disabled. "
                    "This is only acceptable in development.",
                    stacklevel=2,
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION


# Single settings instance imported by the rest of the application.
settings = Settings()
