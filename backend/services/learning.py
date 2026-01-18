import asyncio
from telethon import events
from telethon.tl.types import User
from sqlmodel import Session
from datetime import datetime
from backend.client import client
from backend.database import engine, Message, Fact
from backend.services.ai import ai_service
import logging

logger = logging.getLogger(__name__)

class LearningService:
    def __init__(self):
        self.client = client

    async def start_listening(self):
        """Registers event handlers for incoming messages."""
        logger.info("Starting LearningService event listener...")
        self.client.add_event_handler(self.handle_new_message, events.NewMessage)

    async def _save_message_to_db(self, msg_data):
        """Runs synchronous DB save in a thread."""
        try:
            with Session(engine) as session:
                msg = Message(**msg_data)
                session.add(msg)
                session.commit()
                session.refresh(msg)
                return msg.id
        except Exception as e:
            logger.error(f"DB Error saving message: {e}")
            return None

    async def _save_facts_to_db(self, facts, source_msg_id, chat_id):
        """Runs synchronous DB save in a thread."""
        try:
            with Session(engine) as session:
                for fact_data in facts:
                    fact = Fact(
                        chat_id=chat_id,
                        entity_name=fact_data["entity"],
                        value=fact_data["value"],
                        category=fact_data.get("category", "general"),
                        source_message_id=source_msg_id
                    )
                    session.add(fact)
                session.commit()
        except Exception as e:
            logger.error(f"DB Error saving facts: {e}")

    async def handle_new_message(self, event):
        """
        Intercepts new messages (incoming and outgoing), saves them to DB,
        triggers AI analysis for fact extraction, and optionally replies.
        """
        try:
            chat_id = event.chat_id
            sender_id = event.sender_id
            text = event.message.message
            msg_id = event.message.id
            date = event.message.date or datetime.utcnow()
            is_outgoing = event.message.out

            sender_name = "Unknown"
            is_bot = False
            if event.sender:
                if isinstance(event.sender, User):
                    is_bot = event.sender.bot

                if hasattr(event.sender, "first_name"):
                    sender_name = f"{event.sender.first_name} {event.sender.last_name or ''}".strip()
                elif hasattr(event.sender, "title"):
                    sender_name = event.sender.title

            msg_data = {
                "telegram_message_id": msg_id,
                "chat_id": chat_id,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "text": text,
                "date": date,
                "is_outgoing": is_outgoing
            }

            # 1. Save to Database (Non-blocking)
            db_message_id = await asyncio.to_thread(self._save_message_to_db, msg_data)

            # 2. Asynchronously extract facts (Learning)
            if text and len(text) > 10 and db_message_id:
                asyncio.create_task(self._analyze_and_extract(text, db_message_id, chat_id))

            # 3. Auto-Reply (Conversation)
            if not is_outgoing and event.is_private and not is_bot:
                asyncio.create_task(self._generate_and_send_reply(chat_id, text))

        except Exception as e:
            logger.error(f"Error in handle_new_message: {e}")

    async def _analyze_and_extract(self, text: str, source_msg_id: int, chat_id: int):
        """Extracts facts using AI service and saves them."""
        facts = await ai_service.extract_facts(text)
        if facts:
            await asyncio.to_thread(self._save_facts_to_db, facts, source_msg_id, chat_id)
            logger.info(f"Learned {len(facts)} new facts from message {source_msg_id}")

    async def _generate_and_send_reply(self, chat_id: int, user_message: str):
        """Generates a response using AI and sends it."""
        try:
            # Simulate typing
            async with self.client.action(chat_id, 'typing'):
                response_text = await ai_service.generate_natural_response(chat_id, user_message)
                if response_text:
                    await self.client.send_message(chat_id, response_text)
        except Exception as e:
            logger.error(f"Error sending reply: {e}")

learning_service = LearningService()
