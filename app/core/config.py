from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://marketforge:marketforge_secret@localhost:5432/marketforge_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    EXCHANGE_RATE_API_KEY: str = ""
    EXCHANGE_RATE_API_URL: str = "https://api.exchangerate-api.com/v4/latest"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@marketforge.example"

    LOG_LEVEL: str = "INFO"

    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_WEBHOOK_SECRET: str = ""

    FLUTTERWAVE_PUBLIC_KEY: str = ""
    FLUTTERWAVE_SECRET_KEY: str = ""
    FLUTTERWAVE_WEBHOOK_SECRET: str = ""

    MONNIFY_API_KEY: str = ""
    MONNIFY_SECRET_KEY: str = ""
    MONNIFY_CONTRACT_CODE: str = ""
    MONNIFY_WEBHOOK_SECRET: str = ""

    DEFAULT_PAYMENT_GATEWAY: str = "stripe"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()