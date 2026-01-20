import asyncio
from telethon import events
from telethon.tl.types import User
from sqlmodel import Session, select
from datetime import datetime, timezone
from backend.client import client
from backend.database import engine, Message, Fact
from backend.services.ai import ai_service
import logging

logger = logging.getLogger(__name__)

class LearningService:
    def __init__(self):
        self.client = client

    async def ingest_history(self, chat_id: int, limit: int = 100):
        """Fetches past messages and saves them to DB. Learns from recent ones."""
        logger.info(f"Starting history ingestion for chat {chat_id}, limit={limit}...")
        try:
            # We need to resolve the entity first
            entity = await self.client.get_entity(chat_id)
            messages = await self.client.get_messages(entity, limit=limit)

            # Convert to list to iterate
            messages_list = list(messages)
            count = 0

            # Process oldest first for logical order in DB
            for msg in reversed(messages_list):
                if not msg.message: continue

                sender_name = "Unknown"
                if msg.sender:
                    if hasattr(msg.sender, "first_name"):
                        sender_name = f"{msg.sender.first_name} {msg.sender.last_name or ''}".strip()
                    elif hasattr(msg.sender, "title"):
                        sender_name = msg.sender.title

                if not sender_name:
                    sender_name = str(msg.sender_id)

                msg_data = {
                    "telegram_message_id": msg.id,
                    "chat_id": chat_id,
                    "sender_id": msg.sender_id,
                    "sender_name": sender_name,
                    "text": msg.message,
                    "date": msg.date,
                    "is_outgoing": msg.out
                }

                db_id = await asyncio.to_thread(self._save_message_to_db, msg_data)
                if db_id:
                    count += 1

            # Trigger learning on the last 20 USER messages (most recent)
            relevant_msgs = [m for m in messages_list if not m.out and m.message][:20]
            for m in relevant_msgs:
                 asyncio.create_task(self._analyze_and_extract(m.message, m.id, chat_id))

            logger.info(f"Ingested {count} messages for chat {chat_id}.")
            return count
        except Exception as e:
            logger.error(f"Error ingesting history: {e}")
            return 0

    async def start_listening(self):
        """Registers event handlers for incoming messages."""
        logger.info("Starting LearningService event listener...")
        self.client.add_event_handler(self.handle_new_message, events.NewMessage)

    async def _save_message_to_db(self, msg_data):
        """Runs synchronous DB save in a thread."""
        try:
            with Session(engine) as session:
                # Check for duplicate
                existing = session.exec(select(Message).where(Message.telegram_message_id == msg_data["telegram_message_id"], Message.chat_id == msg_data["chat_id"])).first()
                if existing:
                    return existing.id

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
            date = event.message.date or datetime.now(timezone.utc)
            is_outgoing = event.message.out

            sender_name = "Unknown"
            is_bot = False
            if event.sender:
                if isinstance(event.sender, User):
                    is_bot = event.sender.bot
                    sender_name = f"{event.sender.first_name} {event.sender.last_name or ''}".strip()
                elif hasattr(event.sender, "title"):
                    sender_name = event.sender.title

            # Use User ID if name is empty
            if not sender_name:
                sender_name = str(sender_id)

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
            # Only learn from non-trivial messages
            if text and len(text) > 10 and db_message_id:
                asyncio.create_task(self._analyze_and_extract(text, db_message_id, chat_id))

            # 3. Auto-Reply (Conversation)
            # Reply if:
            # - It's a private chat
            # - Not outgoing (from me)
            # - Not from a bot
            # - Message is not empty
            if not is_outgoing and event.is_private and not is_bot and text:
                # Add a "typing" delay to feel natural
                asyncio.create_task(self._generate_and_send_reply(chat_id, text))

        except Exception as e:
            logger.error(f"Error in handle_new_message: {e}")

    async def _analyze_and_extract(self, text: str, source_msg_id: int, chat_id: int):
        """Extracts facts using AI service and saves them."""
        try:
            facts = await ai_service.extract_facts(text)
            if facts:
                await asyncio.to_thread(self._save_facts_to_db, facts, source_msg_id, chat_id)
                logger.info(f"Learned {len(facts)} new facts from message {source_msg_id}")
        except Exception as e:
            logger.error(f"Error in fact extraction: {e}")

    async def _generate_and_send_reply(self, chat_id: int, user_message: str):
        """Generates a response using AI and sends it."""
        try:
            # Simulate processing/typing time (min 1 sec, max 4 sec based on length)
            delay = min(4, max(1, len(user_message) / 50))
            await asyncio.sleep(delay)

            async with self.client.action(chat_id, 'typing'):
                # Generate response
                response_text = await ai_service.generate_natural_response(chat_id, user_message)

                # Wait a bit more to simulate typing the response
                typing_delay = min(5, len(response_text) / 20)
                await asyncio.sleep(typing_delay)

                if response_text:
                    await self.client.send_message(chat_id, response_text)
        except Exception as e:
            logger.error(f"Error sending reply: {e}")

learning_service = LearningService()
