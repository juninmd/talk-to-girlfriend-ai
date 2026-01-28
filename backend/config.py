import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "telegram_session")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "")

# AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
AI_CONTEXT_FACT_LIMIT = int(os.getenv("AI_CONTEXT_FACT_LIMIT", 1000))

# Conversation
CONVERSATION_MIN_DELAY = float(os.getenv("CONVERSATION_MIN_DELAY", 1.0))
CONVERSATION_MAX_DELAY = float(os.getenv("CONVERSATION_MAX_DELAY", 4.0))
CONVERSATION_TYPING_SPEED = float(os.getenv("CONVERSATION_TYPING_SPEED", 0.05))

# Reporting
REPORT_CHANNEL_ID_STR = os.getenv("REPORT_CHANNEL_ID")
REPORT_CHANNEL_ID = int(REPORT_CHANNEL_ID_STR) if REPORT_CHANNEL_ID_STR else None

# Learning
LEARNING_BATCH_SIZE = int(os.getenv("LEARNING_BATCH_SIZE", 5))
LEARNING_DELAY = float(os.getenv("LEARNING_DELAY", 1.0))
