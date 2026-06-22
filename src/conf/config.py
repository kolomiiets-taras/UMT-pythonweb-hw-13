from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Database
    DB_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/contacts"

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # JWT
    JWT_SECRET: str = "change-me-super-secret-key-min-32-bytes-long-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_TOKEN_EXPIRE_HOURS: int = 24
    RESET_TOKEN_EXPIRE_HOURS: int = 1

    # Redis (cache)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    USER_CACHE_TTL: int = 900

    # Mail (SMTP)
    MAIL_USERNAME: str = "example@meta.ua"
    MAIL_PASSWORD: str = "secret"
    MAIL_FROM: str = "example@meta.ua"
    MAIL_PORT: int = 465
    MAIL_SERVER: str = "smtp.meta.ua"
    MAIL_FROM_NAME: str = "Contacts API"

    # Cloudinary
    CLD_NAME: str = "cloud-name"
    CLD_API_KEY: str = "0000000000"
    CLD_API_SECRET: str = "secret"

    # Base URL used to build links in emails
    BASE_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )


settings = Settings()
