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

# Reporting
REPORT_CHANNEL_ID_STR = os.getenv("REPORT_CHANNEL_ID")
REPORT_CHANNEL_ID = int(REPORT_CHANNEL_ID_STR) if REPORT_CHANNEL_ID_STR else None
