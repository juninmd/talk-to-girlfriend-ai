import asyncio
import logging
from telethon import events
from telethon.tl.types import User
from backend.client import client
from backend.services.ai import ai_service

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self):
        self.client = client

    async def handle_incoming_message(self, event):
        """
        Handles incoming messages and decides whether to reply.
        """
        try:
            # Basic checks: Private, Not outgoing, Not bot, Has text
            if event.message.out or not event.is_private or not event.message.message:
                return

            # Check if sender is a bot
            if event.sender and isinstance(event.sender, User) and event.sender.bot:
                return

            text = event.message.message
            chat_id = event.chat_id

            # Trigger reply
            asyncio.create_task(self._generate_and_send_reply(chat_id, text))

        except Exception as e:
            logger.error(f"Error in ConversationService handler: {e}")

    async def _generate_and_send_reply(self, chat_id: int, user_message: str):
        """Generates a response using AI and sends it."""
        try:
            # Simulate processing/typing time (min 1 sec, max 4 sec based on length)
            delay = min(4, max(1, len(user_message) / 50))
            await asyncio.sleep(delay)

            async with self.client.action(chat_id, "typing"):
                # Generate response
                response_text = await ai_service.generate_natural_response(chat_id, user_message)

                # Wait a bit more to simulate typing the response
                typing_delay = min(5, len(response_text) / 20)
                await asyncio.sleep(typing_delay)

                if response_text:
                    await self.client.send_message(chat_id, response_text)
                    logger.info(f"Sent reply to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error sending reply to {chat_id}: {e}")

conversation_service = ConversationService()
