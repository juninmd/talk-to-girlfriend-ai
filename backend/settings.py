from typing import Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_SESSION_NAME: str = "telegram_session"
    TELEGRAM_SESSION_STRING: str = ""

    # AI
    GOOGLE_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gemini-1.5-flash"
    AI_CONTEXT_FACT_LIMIT: int = 50

    # Conversation
    CONVERSATION_MIN_DELAY: float = 1.0
    CONVERSATION_MAX_DELAY: float = 4.0
    CONVERSATION_TYPING_SPEED: float = 0.05

    # Reporting
    REPORT_CHANNEL_ID: Optional[Union[int, str]] = None
    REPORT_TIME_HOUR: int = 8
    REPORT_TIME_MINUTE: int = 0
    REPORT_CONTEXT_LIMIT: int = 2000

    # Learning
    LEARNING_BATCH_SIZE: int = 5
    LEARNING_DELAY: float = 1.0
    MIN_MESSAGE_LENGTH_FOR_LEARNING: int = 10
    LEARNING_HISTORY_LIMIT: int = 50
    AUTO_LEARN_ON_STARTUP: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"  # Ignore extra env vars
    )


settings = Settings()
