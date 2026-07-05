"""Centralized config loaded from environment."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # Database
    MONGO_URL: str = os.environ["MONGO_URL"]
    DB_NAME: str = os.environ.get("DB_NAME", "whatsapp_saas")

    # CORS
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")

    # Auth / crypto
    JWT_SIGNING_KEY: str = os.environ["JWT_SIGNING_KEY"]
    TOKEN_ENCRYPTION_KEY: str = os.environ["TOKEN_ENCRYPTION_KEY"]
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 14
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # Meta
    META_APP_ID: str = os.environ.get("META_APP_ID", "")
    META_APP_SECRET: str = os.environ.get("META_APP_SECRET", "mock-app-secret")
    META_EMBEDDED_SIGNUP_CONFIG_ID: str = os.environ.get("META_EMBEDDED_SIGNUP_CONFIG_ID", "")
    META_WEBHOOK_VERIFY_TOKEN: str = os.environ.get("META_WEBHOOK_VERIFY_TOKEN", "mock-verify-token")
    META_GRAPH_API_VERSION: str = os.environ.get("META_GRAPH_API_VERSION", "v21.0")
    META_MOCK_MODE: bool = os.environ.get("META_MOCK_MODE", "true").lower() == "true"

    # Worker
    WORKER_ENABLED: bool = os.environ.get("WORKER_ENABLED", "true").lower() == "true"
    WORKER_POLL_INTERVAL_MS: int = int(os.environ.get("WORKER_POLL_INTERVAL_MS", "500"))

    # Rate limit (per phone number per minute)
    SEND_RATE_LIMIT_PER_MIN: int = 60


settings = Settings()
