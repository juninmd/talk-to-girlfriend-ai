import asyncio
import logging
from dataclasses import dataclass
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


@dataclass
class LearningResult:
    messages_count: int
    facts_count: int
    message: str


class LearningService:
    """
    Service responsible for ingesting chat history and extracting facts (learning).
    """

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

    async def ingest_history(
        self, chat_id: int, limit: int = 100, force_rescan: bool = False
    ) -> LearningResult:
        """
        Fetches past messages and saves them to DB. Learns from recent ones.
        Returns a LearningResult object.

        Args:
            chat_id: The ID of the chat to learn from.
            limit: Number of messages to fetch.
            force_rescan: If True, ignores last synced ID and fetches latest messages (backfill).
        """
        logger.info(
            f"Starting history ingestion for chat {chat_id}, limit={limit}, force_rescan={force_rescan}..."
        )
        try:
            min_id = 0
            if not force_rescan:
                min_id = self._get_last_synced_id(chat_id)

            entity = await self.client.get_entity(chat_id)

            messages = await self._fetch_history_messages(entity, limit, min_id)
            count = await self._process_messages_ingestion(chat_id, messages)

            relevant_msgs = self._filter_relevant_messages(messages)
            facts_count = await self._process_learning_batch(chat_id, relevant_msgs)

            if count == 0:
                msg = "No new messages found to ingest."
            else:
                msg = f"Ingested {count} new messages. Learned {facts_count} new facts."

            logger.info(f"Chat {chat_id}: {msg}")
            return LearningResult(
                messages_count=count,
                facts_count=facts_count,
                message=msg,
            )
        except Exception as e:
            logger.error(f"Error ingesting history: {e}")
            return LearningResult(
                messages_count=0,
                facts_count=0,
                message=f"Error: {str(e)}",
            )

    async def ingest_all_history(self, limit_dialogs: int = 10, msgs_limit: int = 30) -> str:
        """
        Iterates over the most recent dialogs and ingests history for each.
        """
        try:
            dialogs = await self.client.get_dialogs(limit=limit_dialogs)
            total_learned = 0
            chats_processed = 0

            for dialog in dialogs:
                if dialog.is_channel:
                    continue  # Skip channels to focus on conversations

                # Ingest history for this chat
                result = await self.ingest_history(dialog.id, limit=msgs_limit, force_rescan=False)
                total_learned += result.facts_count
                chats_processed += 1

                if chats_processed % 5 == 0:
                    logger.info(
                        f"Global Ingestion: Processed {chats_processed}/{len(dialogs)} chats so far..."
                    )

                # Sleep to avoid hitting rate limits too hard
                await asyncio.sleep(2)

            return f"Processed {chats_processed} chats. Total new facts learned: {total_learned}."
        except Exception as e:
            logger.error(f"Error in global ingestion: {e}")
            return f"Error: {str(e)}"

    async def _fetch_history_messages(self, entity: Any, limit: int, min_id: int) -> List[Any]:
        """
        Fetches messages strictly newer than min_id with retry logic for FloodWaitError.
        Returns a list of Telethon Message objects.
        """
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            try:
                # Telethon get_messages returns an iterator-like object, need to list() it
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
        """Gets the last synced telegram_message_id for a chat from the DB."""
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

    def _create_message_data(self, msg: Any, chat_id: int) -> Dict[str, Any]:
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

    async def _process_messages_ingestion(self, chat_id: int, messages_list: List[Any]) -> int:
        """Saves messages to DB and returns count of new messages."""
        count = 0
        # Process oldest first for logical order in DB
        for msg in reversed(messages_list):
            if not msg.message:
                logger.debug(f"Skipping empty message ID {msg.id} in chat {chat_id}")
                continue

            msg_data = self._create_message_data(msg, chat_id)

            db_id = await asyncio.to_thread(self._save_message_to_db, msg_data)
            if db_id:
                count += 1
        return count

    def _filter_relevant_messages(self, messages_list: List[Any]) -> List[Any]:
        """Filters messages relevant for learning (text length, not reports)."""
        return [
            m
            for m in messages_list
            if m.message
            and len(m.message) >= settings.MIN_MESSAGE_LENGTH_FOR_LEARNING
            and not m.message.startswith(REPORT_PREFIXES)
        ]

    async def _process_learning_batch(self, chat_id: int, relevant_msgs: List[Any]) -> int:
        """Processes learning (fact extraction) in batches. Returns total facts found."""
        batch_size = settings.LEARNING_BATCH_SIZE
        total_batches = (len(relevant_msgs) + batch_size - 1) // batch_size
        total_facts = 0

        for i in range(0, len(relevant_msgs), batch_size):
            batch_num = (i // batch_size) + 1
            logger.info(
                f"Processing learning batch {batch_num}/{total_batches} for chat {chat_id}..."
            )

            batch = relevant_msgs[i : i + batch_size]
            tasks = []
            for m in batch:
                tasks.append(self._analyze_and_extract_safe(m.message, m.id, chat_id, m.sender_id))

            # Run batch and wait a bit
            results = await asyncio.gather(*tasks)
            total_facts += sum(results)
            await asyncio.sleep(settings.LEARNING_DELAY)

        return total_facts

    async def start_listening(self):
        """Registers event handlers for incoming messages."""
        logger.info("Starting LearningService event listener...")
        self.client.add_event_handler(self.handle_message_learning, events.NewMessage)

        if settings.AUTO_LEARN_ON_STARTUP:
            asyncio.create_task(self._background_backfill_task())

    def _check_if_learning_needed(self) -> bool:
        """Checks if the database has very few facts, indicating need for backfill."""
        try:
            with Session(engine) as session:
                # Check if we have less than 10 facts
                statement = select(func.count(Fact.id))
                count = session.exec(statement).one()
                return count < 10
        except Exception as e:
            logger.error(f"Error checking knowledge base size: {e}")
            return False

    async def _background_backfill_task(self):
        """Background task to backfill history if needed."""
        logger.info("Auto-learning: Checking if backfill is needed...")
        try:
            # Run check in thread to avoid blocking
            needed = await asyncio.to_thread(self._check_if_learning_needed)
            if needed:
                logger.info("Auto-learning: Backfill needed. Starting in 10 seconds...")
                # Give time for connection to stabilize
                await asyncio.sleep(10)
                await self.ingest_all_history(
                    limit_dialogs=10, msgs_limit=settings.LEARNING_HISTORY_LIMIT
                )
            else:
                logger.info("Auto-learning: Knowledge base sufficient. Skipping backfill.")
        except Exception as e:
            logger.error(f"Auto-learning failed: {e}", exc_info=True)

    async def _save_message_to_db(self, msg_data: Dict[str, Any]) -> Optional[int]:
        """Runs synchronous DB save in a thread. Returns DB ID if saved, None if error/duplicate."""
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
        self,
        facts: List[Dict[str, Any]],
        source_msg_id: int,
        chat_id: int,
        sender_id: Optional[int] = None,
    ):
        """Runs synchronous DB save of facts in a thread."""
        try:
            with Session(engine) as session:
                for fact_data in facts:
                    fact = Fact(
                        chat_id=chat_id,
                        sender_id=sender_id,
                        entity_name=fact_data["entity"],
                        value=fact_data["value"],
                        category=fact_data.get("category", "general"),
                        source_message_id=source_msg_id,
                    )
                    session.add(fact)
                session.commit()
        except Exception as e:
            logger.error(f"DB Error saving facts: {e}")

    async def handle_message_learning(self, event: events.NewMessage.Event):
        """
        Intercepts new messages (incoming and outgoing), saves them to DB,
        and triggers AI analysis for fact extraction.
        """
        try:
            chat_id = event.chat_id
            text = event.message.message
            is_outgoing = event.message.out

            msg_data = self._create_message_data(event.message, chat_id)
            sender_id = msg_data.get("sender_id")

            # 1. Save to Database (Non-blocking)
            db_message_id = await asyncio.to_thread(self._save_message_to_db, msg_data)

            # 2. Asynchronously extract facts (Learning)
            if text and len(text) >= settings.MIN_MESSAGE_LENGTH_FOR_LEARNING and db_message_id:
                # Avoid learning from our own generated reports
                if text.startswith(REPORT_PREFIXES):
                    return

                # If we are a bot (Bot API), never learn from our own outgoing messages (replies).
                # If we are a Userbot (me.bot=False), we DO learn from our outgoing messages
                # because they represent the user's voice/facts.
                me = await self._get_me()
                if me and me.bot and is_outgoing:
                    return

                asyncio.create_task(
                    self._analyze_and_extract(text, db_message_id, chat_id, sender_id)
                )

        except Exception as e:
            logger.error(f"Error in handle_message_learning: {e}")

    def _check_facts_exist(self, source_msg_id: int) -> bool:
        """Checks if facts already exist for a given source message ID."""
        with Session(engine) as session:
            statement = select(Fact).where(Fact.source_message_id == source_msg_id)
            result = session.exec(statement).first()
            return result is not None

    async def _analyze_and_extract(
        self, text: str, source_msg_id: int, chat_id: int, sender_id: Optional[int] = None
    ) -> int:
        """Extracts facts using AI service and saves them. Returns number of facts found."""
        try:
            # Check if facts already exist for this message to avoid duplicates
            existing_facts = await asyncio.to_thread(self._check_facts_exist, source_msg_id)
            if existing_facts:
                return 0

            facts = await ai_service.extract_facts(text)
            if facts:
                await asyncio.to_thread(
                    self._save_facts_to_db, facts, source_msg_id, chat_id, sender_id
                )
                logger.info(f"Learned {len(facts)} new facts from message {source_msg_id}")
                return len(facts)
            return 0
        except Exception as e:
            logger.error(f"Error in fact extraction: {e}")
            return 0

    async def _analyze_and_extract_safe(
        self, text: str, source_msg_id: int, chat_id: int, sender_id: Optional[int] = None
    ) -> int:
        """Wrapper for extraction that catches all exceptions. Returns 0 on error."""
        try:
            return await self._analyze_and_extract(text, source_msg_id, chat_id, sender_id)
        except Exception as e:
            logger.error(
                f"Failed to process message {source_msg_id} for learning: {e}", exc_info=True
            )
            return 0


learning_service = LearningService()
