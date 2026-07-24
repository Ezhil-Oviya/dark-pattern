from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Dark Pattern Compliance Auditor API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "dark_pattern_auditor"
    jwt_secret_key: str = "replace-with-secure-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    evidence_storage_path: str = "../storage/evidence"
    report_storage_path: str = "../storage/reports"
    playwright_headless: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
