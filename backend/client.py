from telethon import TelegramClient
from telethon.sessions import StringSession
from backend.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME, SESSION_STRING

def get_client():
    if SESSION_STRING:
        return TelegramClient(StringSession(SESSION_STRING), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    else:
        return TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)

client = get_client()
