from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_env: str = "development"
    app_debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    secret_key: str = "change-me-in-production"
    
    database_url: str = "postgresql+psycopg://postgres:sellflow_password@localhost:5432/postgres"

settings = Settings()
