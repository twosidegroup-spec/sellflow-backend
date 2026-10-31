"""Application configuration with fail-closed behaviour in production.

Security policy (after the System A -> System B migration):

* In production (`APP_ENV=production`), a real `SECRET_KEY` is mandatory.
  Placeholder values and values shorter than 32 characters are rejected and
  the process refuses to start (fail closed). This replaces the previous
  behaviour where a missing `.env` silently produced JWTs signed with a
  public placeholder key.
* In production a real `DEVICE_TOKEN_SECRET` is mandatory. It is the HMAC
  key that protects device-bridge pairing codes and device tokens. There is
  no development fallback in production; outside production a cryptographically
  random secret is generated per process (see `app/core/device_tokens.py`).
* CORS origins are an explicit list. `*` is permitted only when credentials
  are disabled, so the unsafe `allow_origins=["*"] + allow_credentials=True`
  combination cannot occur.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRETS = {
    "your-32-character-secret-key-generate-with-openssl",
    "your-32-character-secret-key-here",
    "changeme",
    "change-me",
    "change_me",
    "secret",
    "dev-secret",
    "please-change-me",
    "payment-bridge-dev-secret-change-me",
}

_PRODUCTION_ENVS = {"production", "prod"}

_DEFAULT_CORS_ORIGINS = (
    "http://localhost,http://localhost:8000,http://localhost:3000,"
    "http://127.0.0.1,http://127.0.0.1:8000"
)

_MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==================== ENVIRONMENT ====================
    app_env: str = "development"
    app_debug: bool = False

    # ==================== DATABASE ====================
    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/sellflow_db"

    # ==================== SECURITY ====================
    secret_key: str = "your-32-character-secret-key-generate-with-openssl"
    cors_origins: str = _DEFAULT_CORS_ORIGINS

    # HMAC key for device-bridge pairing codes and device tokens.
    # Mandatory in production (validated below).
    device_token_secret: str = ""

    # Optional shared invitation code for seller registration. When set, the
    # register endpoint requires a matching `invite_code`.
    registration_invite_code: str = ""

    # ==================== CLOUD STORAGE ====================
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = ""
    aws_s3_endpoint: str = ""

    # ==================== FILE UPLOAD ====================
    max_upload_size: int = 10 * 1024 * 1024
    allowed_upload_types: str = "image/jpeg,image/png,image/jpg"

    # ==================== DERIVED ====================
    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in _PRODUCTION_ENVS

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        if not raw:
            raw = _DEFAULT_CORS_ORIGINS
        return [part.strip() for part in raw.split(",") if part.strip()]

    @property
    def cors_allow_credentials(self) -> bool:
        # Credentials must never ride on a wildcard origin.
        return "*" not in self.cors_origin_list

    @property
    def allowed_upload_type_list(self) -> list[str]:
        return [t.strip().lower() for t in self.allowed_upload_types.split(",") if t.strip()]

    # ==================== VALIDATION ====================
    @model_validator(mode="after")
    def _fail_closed_in_production(self) -> "Settings":
        if not self.is_production:
            return self

        secret = (self.secret_key or "").strip()
        if (
            not secret
            or len(secret) < _MIN_SECRET_LENGTH
            or secret.casefold() in _PLACEHOLDER_SECRETS
        ):
            raise ValueError(
                "SECRET_KEY is missing, too short, or a known placeholder while "
                f"APP_ENV={self.app_env!r}. Production requires a unique key of at "
                'least 32 characters. Generate one with: python -c "import secrets; '
                'print(secrets.token_hex(32))"'
            )

        device_secret = (self.device_token_secret or "").strip()
        if (
            not device_secret
            or len(device_secret) < _MIN_SECRET_LENGTH
            or device_secret.casefold() in _PLACEHOLDER_SECRETS
        ):
            raise ValueError(
                "DEVICE_TOKEN_SECRET is missing or unusable while "
                f"APP_ENV={self.app_env!r}. It protects device pairing codes and "
                "device tokens, so production refuses to start without it. "
                'Generate one with: python -c "import secrets; print(secrets.'
                'token_urlsafe(48))"'
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
