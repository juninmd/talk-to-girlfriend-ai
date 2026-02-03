import asyncio
from telethon import events
from sqlmodel import Session, select, func
from datetime import datetime, timezone
from backend.client import client
from backend.database import engine, Message, Fact
from backend.services.ai import ai_service
from backend.settings import settings
from backend.utils import get_sender_name
import logging

logger = logging.getLogger(__name__)


class LearningService:
    def __init__(self):
        self.client = client
        self._me = None

    async def _get_me(self):
        if not self._me:
            try:
                self._me = await self.client.get_me()
            except Exception:
                pass
        return self._me

    async def ingest_history(self, chat_id: int, limit: int = 100):
        """Fetches past messages and saves them to DB. Learns from recent ones."""
        logger.info(f"Starting history ingestion for chat {chat_id}, limit={limit}...")
        try:
            min_id = self._get_last_synced_id(chat_id)

            # We need to resolve the entity first
            entity = await self.client.get_entity(chat_id)

            # Fetch messages strictly newer than min_id
            messages = await self.client.get_messages(entity, limit=limit, min_id=min_id)
            messages_list = list(messages)

            count = await self._process_messages_ingestion(chat_id, messages_list)

            # Trigger learning on extracted messages
            relevant_msgs = self._filter_relevant_messages(messages_list)
            await self._process_learning_batch(chat_id, relevant_msgs)

            logger.info(
                f"Ingested {count} messages for chat {chat_id}. Analyzed {len(relevant_msgs)} for facts."
            )
            return count
        except Exception as e:
            logger.error(f"Error ingesting history: {e}")
            return 0

    def _get_last_synced_id(self, chat_id: int) -> int:
        with Session(engine) as session:
            statement = select(func.max(Message.telegram_message_id)).where(
                Message.chat_id == chat_id
            )
            result = session.exec(statement).first()
            if result:
                logger.info(
                    f"Found existing history for chat {chat_id}. Resuming from ID {result}."
                )
                return result
        return 0

    async def _process_messages_ingestion(self, chat_id, messages_list):
        count = 0
        # Process oldest first for logical order in DB
        for msg in reversed(messages_list):
            if not msg.message:
                continue

            sender_name = get_sender_name(msg)
            if sender_name == "Unknown":
                sender_name = str(msg.sender_id)

            msg_data = {
                "telegram_message_id": msg.id,
                "chat_id": chat_id,
                "sender_id": msg.sender_id,
                "sender_name": sender_name,
                "text": msg.message,
                "date": msg.date,
                "is_outgoing": msg.out,
            }

            db_id = await asyncio.to_thread(self._save_message_to_db, msg_data)
            if db_id:
                count += 1
        return count

    def _filter_relevant_messages(self, messages_list):
        return [
            m
            for m in messages_list
            if m.message
            and len(m.message) > 5
            and not (
                m.message.startswith("# 📅 Relatório Diário")
                or m.message.startswith("# 📅 Relatório")
            )
        ]

    async def _process_learning_batch(self, chat_id, relevant_msgs):
        # Analyze in batches to avoid overwhelming the API
        batch_size = settings.LEARNING_BATCH_SIZE
        total_batches = (len(relevant_msgs) + batch_size - 1) // batch_size

        for i in range(0, len(relevant_msgs), batch_size):
            batch_num = (i // batch_size) + 1
            logger.info(
                f"Processing learning batch {batch_num}/{total_batches} for chat {chat_id}..."
            )

            batch = relevant_msgs[i : i + batch_size]
            tasks = []
            for m in batch:
                tasks.append(self._analyze_and_extract_safe(m.message, m.id, chat_id))

            # Run batch and wait a bit
            await asyncio.gather(*tasks)
            await asyncio.sleep(settings.LEARNING_DELAY)

    async def start_listening(self):
        """Registers event handlers for incoming messages."""
        logger.info("Starting LearningService event listener...")
        self.client.add_event_handler(self.handle_message_learning, events.NewMessage)

    async def _save_message_to_db(self, msg_data):
        """Runs synchronous DB save in a thread."""
        try:
            with Session(engine) as session:
                # Check for duplicate
                existing = session.exec(
                    select(Message).where(
                        Message.telegram_message_id == msg_data["telegram_message_id"],
                        Message.chat_id == msg_data["chat_id"],
                    )
                ).first()
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
                        source_message_id=source_msg_id,
                    )
                    session.add(fact)
                session.commit()
        except Exception as e:
            logger.error(f"DB Error saving facts: {e}")

    async def handle_message_learning(self, event):
        """
        Intercepts new messages (incoming and outgoing), saves them to DB,
        and triggers AI analysis for fact extraction.
        """
        try:
            chat_id = event.chat_id
            sender_id = event.sender_id
            text = event.message.message
            msg_id = event.message.id
            date = event.message.date or datetime.now(timezone.utc)
            is_outgoing = event.message.out

            sender_name = get_sender_name(event.message)
            if sender_name == "Unknown":
                sender_name = str(sender_id)

            msg_data = {
                "telegram_message_id": msg_id,
                "chat_id": chat_id,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "text": text,
                "date": date,
                "is_outgoing": is_outgoing,
            }

            # 1. Save to Database (Non-blocking)
            db_message_id = await asyncio.to_thread(self._save_message_to_db, msg_data)

            # 2. Asynchronously extract facts (Learning)
            # Learn from both incoming and outgoing, but filter out Reports
            if text and len(text) > 10 and db_message_id:
                # Avoid learning from our own generated reports
                if text.startswith("# 📅 Relatório Diário") or text.startswith("# 📅 Relatório"):
                    return

                # If we are a bot, never learn from our own outgoing messages
                me = await self._get_me()
                if me and me.bot and is_outgoing:
                    return

                asyncio.create_task(self._analyze_and_extract(text, db_message_id, chat_id))

        except Exception as e:
            logger.error(f"Error in handle_message_learning: {e}")

    async def _analyze_and_extract(self, text: str, source_msg_id: int, chat_id: int):
        """Extracts facts using AI service and saves them."""
        try:
            facts = await ai_service.extract_facts(text)
            if facts:
                await asyncio.to_thread(self._save_facts_to_db, facts, source_msg_id, chat_id)
                logger.info(f"Learned {len(facts)} new facts from message {source_msg_id}")
        except Exception as e:
            logger.error(f"Error in fact extraction: {e}")

    async def _analyze_and_extract_safe(self, text: str, source_msg_id: int, chat_id: int):
        """Wrapper for extraction that catches all exceptions to prevent batch failure."""
        try:
            await self._analyze_and_extract(text, source_msg_id, chat_id)
        except Exception as e:
            logger.error(f"Failed to process message {source_msg_id} for learning: {e}")


learning_service = LearningService()
