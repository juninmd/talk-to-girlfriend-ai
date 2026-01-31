from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_SESSION_NAME: str = "telegram_session"
    TELEGRAM_SESSION_STRING: str = ""

    # AI
    GOOGLE_API_KEY: Optional[str] = None
    AI_CONTEXT_FACT_LIMIT: int = 1000

    # Conversation
    CONVERSATION_MIN_DELAY: float = 1.0
    CONVERSATION_MAX_DELAY: float = 4.0
    CONVERSATION_TYPING_SPEED: float = 0.05

    # Reporting
    REPORT_CHANNEL_ID: Optional[int] = None

    # Learning
    LEARNING_BATCH_SIZE: int = 5
    LEARNING_DELAY: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"  # Ignore extra env vars
    )


settings = Settings()
