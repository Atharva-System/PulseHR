"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the HR AI Platform."""

    nvidia_api_key: str = ""
    model_name: str = "openai/gpt-oss-120b"
    log_level: str = "INFO"
    app_name: str = "HR AI Platform"
    app_version: str = "1.0.0"
    database_url: str = ""  # e.g. postgresql://user:pass@localhost:5432/hr_ai

    # JWT settings
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # SMTP settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "hr-platform@company.com"
    smtp_to_hr: str = "hr-team@company.com"
    smtp_to_authority: str = "authority@company.com"

    # Initial admin seed for new databases
    admin_username: str = "ceo@1"
    admin_email: str = "admin1@yopmail.com"
    admin_full_name: str = "Administrator"
    admin_password: str = "admin123"
    admin_role: str = "higher_authority"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
settings = Settings()
