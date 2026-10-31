from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ==================== PRODUCTION ENVIRONMENT ====================
    # Set to 'production' for deployment, 'development' for local
    app_env: str = "development"
    app_debug: bool = False  # Set to True for local development only

    # ==================== DATABASE ====================
    # REQUIRED FOR PRODUCTION: Set DATABASE_URL in your hosting environment
    # Example: postgresql+psycopg://user:pass@host:5432/sellflow_db
    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/sellflow_db"

    # ==================== SECURITY ====================
    # REQUIRED FOR PRODUCTION: Generate 32+ char key with: openssl rand -hex 32
    # NEVER commit your real secret to GitHub
    secret_key: str = "your-32-character-secret-key-generate-with-openssl"

    # ==================== CORS ====================
    # Set to specific domain in production: https://your-app.com
    # Development can use localhost variants
    cors_origins: str = "http://localhost,http://localhost:8000,http://localhost:3000,http://127.0.0.1,*"

    # ==================== CLOUD STORAGE (Optional - for file uploads) ====================
    # Set these for cloud storage (Cloudflare R2, AWS S3, etc.)
    # Leave empty to use local file storage (NOT recommended for production)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = ""
    aws_s3_endpoint: str = ""

    # ==================== FILE UPLOAD ====================
    # Maximum upload size in bytes (10MB default)
    max_upload_size: int = 10 * 1024 * 1024

    # Allowed file types
    allowed_upload_types: str = "image/jpeg,image/png,image/jpg"


settings = Settings()
