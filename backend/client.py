from telethon import TelegramClient
from telethon.sessions import StringSession
from backend.settings import settings
import logging

logger = logging.getLogger(__name__)


# Mock for testing environment if API keys are missing
class MockClient:
    def __init__(self, *args, **kwargs):
        pass

    async def start(self):
        logger.warning("MockClient started (No API credentials provided)")

    def add_event_handler(self, *args, **kwargs):
        pass

    def action(self, *args, **kwargs):
        class AsyncContext:
            async def __aenter__(self):
                pass

            async def __aexit__(self, *args):
                pass

        return AsyncContext()

    async def send_message(self, *args, **kwargs):
        pass

    async def get_entity(self, *args, **kwargs):
        return None

    async def run_until_disconnected(self):
        pass


def get_client():
    if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
        logger.warning("TELEGRAM_API_ID or TELEGRAM_API_HASH not found. Using MockClient.")
        return MockClient()

    if settings.TELEGRAM_SESSION_STRING:
        return TelegramClient(
            StringSession(settings.TELEGRAM_SESSION_STRING),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
        )
    else:
        return TelegramClient(
            settings.TELEGRAM_SESSION_NAME, settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH
        )


client = get_client()
