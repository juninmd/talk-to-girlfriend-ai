import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Union

from sqlmodel import Session, select
from backend.database import engine, Message
from backend.services.ai import ai_service
from backend.client import client
from backend.settings import settings
from backend.utils import async_retry, format_entity

logger = logging.getLogger(__name__)


class ReportingService:
    """
    Service responsible for generating and delivering daily activity reports.
    """

    def __init__(self):
        self.client = client
        self._title_cache: Dict[int, str] = {}

    @async_retry(max_attempts=3, delay=5.0)
    async def generate_daily_report(self, chat_id: Optional[int] = None) -> str:
        """
        Generates a summary of all conversations from the last 24 hours.

        Args:
            chat_id: If provided, generates report only for this chat and returns text.
                     If None (default), generates global report and sends to configured channel.

        Returns:
            The generated report text.
        """
        report_scope = f"Specific Chat: {chat_id}" if chat_id else "Global Report"
        logger.info(f"Generating daily report ({report_scope})...")

        # 1. Fetch messages
        messages = await asyncio.to_thread(self._fetch_messages_for_report, chat_id)
        if not messages:
            logger.warning("No messages found for today's report.")
            return "Sem mensagens para relatar."

        # 2. Prepare data (grouping & resolving titles)
        final_data = await self._prepare_data_for_ai(messages)

        # 3. Generate Report Content
        report_text = await self._generate_report_content(
            final_data, total_msgs=len(messages), unique_chats=len(final_data)
        )

        # 4. Send Report (if scheduled/global)
        if not chat_id:
            if not settings.REPORT_CHANNEL_ID:
                logger.warning(
                    "REPORT_CHANNEL_ID not set. Global report will be sent to Saved Messages."
                )
            await self._send_report(report_text)

        return report_text

    def _fetch_messages_for_report(self, chat_id: Optional[int] = None) -> List[Message]:
        """Fetches messages in a thread from the last 24 hours (UTC)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        with Session(engine) as session:
            statement = select(Message).where(Message.date >= cutoff)
            if chat_id:
                statement = statement.where(Message.chat_id == chat_id)

            # Limit to prevent memory issues with massive history
            statement = statement.order_by(Message.date.desc()).limit(5000)

            messages = session.exec(statement).all()
            return list(messages)

    async def _prepare_data_for_ai(self, messages: List[Message]) -> Dict[str, List[Message]]:
        """Groups messages by chat and resolves chat titles."""
        grouped_msgs: Dict[int, List[Message]] = {}
        for m in messages:
            if m.chat_id not in grouped_msgs:
                grouped_msgs[m.chat_id] = []
            grouped_msgs[m.chat_id].append(m)

        final_data = await self._resolve_chat_titles(grouped_msgs)
        return final_data

    async def _resolve_chat_titles(
        self, grouped_msgs: Dict[int, List[Message]]
    ) -> Dict[str, List[Message]]:
        """Resolves chat IDs to human-readable titles using asyncio.gather."""
        final_data = {}
        tasks = []
        chat_ids = list(grouped_msgs.keys())

        # Define a helper function for single resolution
        sem = asyncio.Semaphore(10)

        async def resolve_one(cid):
            async with sem:
                title = f"Chat {cid}"
                if cid in self._title_cache:
                    title = self._title_cache[cid]
                else:
                    try:
                        entity = await self.client.get_entity(cid)
                        formatted = format_entity(entity)
                        title = formatted.get("name", title)
                        self._title_cache[cid] = title
                    except Exception as e:
                        logger.warning(f"Could not resolve title for chat {cid}: {e}")
                return cid, title

        # Create tasks
        for cid in chat_ids:
            tasks.append(resolve_one(cid))

        # Run safely
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                continue

            cid, title = result
            unique_key = f"{title} (ID: {cid})"
            final_data[unique_key] = grouped_msgs[cid]

        return final_data

    async def _generate_report_content(
        self, data: Dict[str, List[Message]], total_msgs: int, unique_chats: int
    ) -> str:
        """Calls AI to summarize and formats the final report."""
        stats_text = f"""
- **Total de Mensagens:** {total_msgs}
- **Conversas Ativas:** {unique_chats}
""".strip()

        # Limit data to avoid huge context
        limit = settings.REPORT_CONTEXT_LIMIT
        if limit > 5000:
            logger.warning(
                f"REPORT_CONTEXT_LIMIT ({limit}) is very high. Watch out for API limits."
            )

        if total_msgs > limit:
            logger.warning(f"Too many messages ({total_msgs}). Applying smart truncation...")

            # Smart Truncation:
            # 1. Take top 50 messages from each chat (to ensure diversity)
            # 2. Collect all, sort by date
            # 3. Truncate to limit

            truncated_items = []
            for title, msgs in data.items():
                # Sort chat msgs by date desc (newest first)
                chat_msgs_sorted = sorted(msgs, key=lambda m: m.date, reverse=True)
                # Take top 50
                truncated_items.extend([(title, m) for m in chat_msgs_sorted[:50]])

            # Now sort everything by date desc to apply global limit
            truncated_items.sort(key=lambda x: x[1].date, reverse=True)

            # Global limit
            truncated_items = truncated_items[:limit]

            # Re-group (and sort back to chronological for the report)
            truncated_items.sort(key=lambda x: x[1].date)

            new_data: Dict[str, List[Message]] = {}
            for title, m in truncated_items:
                if title not in new_data:
                    new_data[title] = []
                new_data[title].append(m)

            data = new_data
            stats_text += f"\n(Truncado inteligentemente para {len(truncated_items)} mensagens)"

        summary = await ai_service.summarize_conversations(data)

        today_str = datetime.now().strftime("%d/%m/%Y")
        report_text = f"""# 📅 Relatório Diário de Conversas
**Data:** {today_str}

## 📊 Estatísticas
{stats_text}

## 📝 Resumo
{summary}"""
        return report_text

    async def _send_report(self, report_text: str):
        """Sends the report to the configured channel or fallback."""
        target_entity = await self._resolve_target_entity()

        if not target_entity:
            logger.error("No valid target entity found to send the report.")
            return

        try:
            await self.client.send_message(target_entity, report_text)
            logger.info(
                f"Daily report sent successfully to {target_entity.id} (Title: {getattr(target_entity, 'title', 'Unknown')})."
            )
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")

    def _normalize_channel_id(self, channel_id: Union[int, str]) -> Optional[Union[int, str]]:
        """Normalizes channel ID (trims string, converts to int if possible)."""
        if isinstance(channel_id, int):
            return channel_id

        if isinstance(channel_id, str):
            channel_id = channel_id.strip()
            # Remove quotes if present
            channel_id = channel_id.strip("'").strip('"')

            if not channel_id:
                logger.warning("REPORT_CHANNEL_ID is an empty string.")
                return None

            # Try to convert to int if it looks like one (e.g. "-100...")
            try:
                return int(channel_id)
            except ValueError:
                # Assume it's a username or invite link
                return channel_id

        logger.warning(f"Invalid type for REPORT_CHANNEL_ID: {type(channel_id)}")
        return None

    async def _resolve_target_entity(self) -> Any:
        """
        Resolves the target entity for the report.
        Priority:
        1. Configured REPORT_CHANNEL_ID (if valid).
        2. Fallback to 'Saved Messages' (me).
        """
        target_entity = None
        channel_id = settings.REPORT_CHANNEL_ID

        if channel_id:
            try:
                normalized_id = self._normalize_channel_id(channel_id)
                if normalized_id is None:
                    raise ValueError("Invalid Channel ID format")

                # Fetch Entity
                target_entity = await self.client.get_entity(normalized_id)
                # Log success with entity name if available
                entity_name = format_entity(target_entity).get("name", "Unknown")
                logger.info(f"Resolved REPORT_CHANNEL_ID to {target_entity.id} ({entity_name})")

            except Exception as e:
                logger.warning(
                    f"Could not resolve configured REPORT_CHANNEL_ID ({settings.REPORT_CHANNEL_ID}): {e}"
                )
                target_entity = None

        if not target_entity:
            logger.warning(
                "REPORT_CHANNEL_ID invalid or missing. Falling back to 'Saved Messages'."
            )
            try:
                target_entity = await self.client.get_me()
            except Exception as e:
                logger.error(f"Could not resolve 'me' for fallback report: {e}")
                return None

        return target_entity


reporting_service = ReportingService()
