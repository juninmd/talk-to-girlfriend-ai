import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from telethon import events
from telethon.errors import FloodWaitError
from sqlmodel import Session, select, func
from backend.client import client
from backend.database import engine, Message, Fact
from backend.services.ai import ai_service
from backend.settings import settings
from backend.utils import get_sender_name

logger = logging.getLogger(__name__)

REPORT_PREFIXES = ("# 📅 Relatório Diário", "# 📅 Relatório")


class LearningService:
    def __init__(self):
        self.client = client
        self._me = None

    async def _get_me(self):
        """Lazy load 'me' user."""
        if not self._me:
            try:
                self._me = await self.client.get_me()
            except Exception:
                pass
        return self._me

    async def ingest_history(self, chat_id: int, limit: int = 100) -> str:
        """
        Fetches past messages and saves them to DB. Learns from recent ones.
        Returns a summary string.
        """
        logger.info(f"Starting history ingestion for chat {chat_id}, limit={limit}...")
        try:
            min_id = self._get_last_synced_id(chat_id)
            entity = await self.client.get_entity(chat_id)

            messages = await self._fetch_history_messages(entity, limit, min_id)
            count = await self._process_messages_ingestion(chat_id, messages)

            relevant_msgs = self._filter_relevant_messages(messages)
            await self._process_learning_batch(chat_id, relevant_msgs)

            msg = f"Ingested {count} messages. Analyzed {len(relevant_msgs)} for facts."
            logger.info(f"Chat {chat_id}: {msg}")
            return msg
        except Exception as e:
            logger.error(f"Error ingesting history: {e}")
            return f"Error: {str(e)}"

    async def _fetch_history_messages(self, entity, limit: int, min_id: int):
        """
        Fetches messages strictly newer than min_id with retry logic for FloodWaitError.
        """
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            try:
                messages = await self.client.get_messages(entity, limit=limit, min_id=min_id)
                return list(messages)
            except FloodWaitError as e:
                attempts += 1
                wait_time = e.seconds + 1
                logger.warning(
                    f"FloodWaitError: Sleeping for {wait_time} seconds (Attempt {attempts}/{max_attempts})."
                )
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                break
        return []

    def _get_last_synced_id(self, chat_id: int) -> int:
        """Gets the last synced telegram_message_id for a chat."""
        with Session(engine) as session:
            statement = select(func.max(Message.telegram_message_id)).where(
                Message.chat_id == chat_id
            )
            result = session.exec(statement).first()
            if result is not None:
                logger.info(
                    f"Found existing history for chat {chat_id}. Resuming from ID {result}."
                )
                return result
        return 0

    def _create_message_data(self, msg, chat_id: int) -> Dict[str, Any]:
        """Helper to create message data dict from Telethon message."""
        sender_name = get_sender_name(msg)
        if sender_name == "Unknown":
            sender_name = str(msg.sender_id)

        return {
            "telegram_message_id": msg.id,
            "chat_id": chat_id,
            "sender_id": msg.sender_id,
            "sender_name": sender_name,
            "text": msg.message,
            "date": msg.date or datetime.now(timezone.utc),
            "is_outgoing": msg.out,
        }

    async def _process_messages_ingestion(self, chat_id: int, messages_list: list) -> int:
        """Saves messages to DB and returns count of new messages."""
        count = 0
        # Process oldest first for logical order in DB
        for msg in reversed(messages_list):
            if not msg.message:
                continue

            msg_data = self._create_message_data(msg, chat_id)

            db_id = await asyncio.to_thread(self._save_message_to_db, msg_data)
            if db_id:
                count += 1
        return count

    def _filter_relevant_messages(self, messages_list: list) -> list:
        """Filters messages relevant for learning."""
        return [
            m
            for m in messages_list
            if m.message
            and len(m.message) >= settings.MIN_MESSAGE_LENGTH_FOR_LEARNING
            and not m.message.startswith(REPORT_PREFIXES)
        ]

    async def _process_learning_batch(self, chat_id: int, relevant_msgs: list):
        """Processes learning in batches."""
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

    async def _save_message_to_db(self, msg_data: Dict[str, Any]) -> Optional[int]:
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

    async def _save_facts_to_db(
        self, facts: List[Dict[str, Any]], source_msg_id: int, chat_id: int
    ):
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
            text = event.message.message
            is_outgoing = event.message.out

            msg_data = self._create_message_data(event.message, chat_id)

            # 1. Save to Database (Non-blocking)
            db_message_id = await asyncio.to_thread(self._save_message_to_db, msg_data)

            # 2. Asynchronously extract facts (Learning)
            if text and len(text) >= settings.MIN_MESSAGE_LENGTH_FOR_LEARNING and db_message_id:
                # Avoid learning from our own generated reports
                if text.startswith(REPORT_PREFIXES):
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
            logger.error(
                f"Failed to process message {source_msg_id} for learning: {e}", exc_info=True
            )


learning_service = LearningService()
