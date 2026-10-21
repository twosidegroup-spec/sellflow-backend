from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # TSG Database Settings
    database_url: str = "postgresql+psycopg://postgres:sellflow_password@tsg-db:5432/sellflow_db"

    # TSG App Settings
    app_env: str = "development"
    app_debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = "your_super_secret_key_change_this_in_production"

    # TSG CORS Settings - Allow localhost and all origins for development
    cors_origins: str = "http://localhost,http://localhost:80,http://localhost:3000,http://127.0.0.1,*"


settings = Settings()
